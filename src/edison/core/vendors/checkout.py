"""Vendor checkout operations.

Handles cloning, fetching, and checking out vendor sources
using a hybrid approach: shared bare mirror + project-scoped worktree.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from edison.core.vendors.cache import VendorMirrorCache
from edison.core.vendors.exceptions import VendorCheckoutError
from edison.core.vendors.models import SyncResult, VendorSource
from edison.core.vendors.redaction import redact_git_args, redact_text_credentials

logger = logging.getLogger(__name__)


class VendorCheckout:
    """Manages vendor checkouts using mirror cache + worktrees.

    Uses a two-tier approach:
    1. Shared bare mirror cache (user-level or specified)
    2. Project-scoped worktree checkout from mirror
    """

    def __init__(self, repo_root: Path, cache_dir: Path) -> None:
        """Initialize checkout manager.

        Args:
            repo_root: Path to project repository root
            cache_dir: Path to mirror cache directory
        """
        self.repo_root = repo_root
        self.cache = VendorMirrorCache(cache_dir)

    def sync(self, source: VendorSource, *, force: bool = False) -> SyncResult:
        """Sync a vendor source.

        Creates or updates the vendor checkout:
        1. Clone/fetch mirror from remote
        2. Checkout worktree at specified ref
        3. Apply sparse checkout if configured

        Args:
            source: Vendor source configuration
            force: Force checkout even if already at correct commit

        Returns:
            SyncResult with success status and resolved commit
        """
        try:
            # Ensure cache directory exists
            self.cache.ensure_cache_dir()

            # Get or create mirror
            mirror_path = self._ensure_mirror(source.url)

            # Fetch latest from remote
            self._fetch_mirror(mirror_path, source.url)

            # Resolve ref to commit
            commit = self._resolve_ref(mirror_path, source.ref)

            # Create/update checkout
            checkout_path = self.repo_root / source.path
            self._checkout(mirror_path, checkout_path, commit, source.sparse, force=force)

            return SyncResult(
                vendor_name=source.name,
                success=True,
                commit=commit,
            )

        except Exception as e:
            return SyncResult(
                vendor_name=source.name,
                success=False,
                error=str(e),
            )

    def _ensure_mirror(self, url: str) -> Path:
        """Ensure mirror exists for URL.

        Args:
            url: Git repository URL

        Returns:
            Path to mirror repository
        """
        mirror_path = self.cache.get_mirror_path(url)

        if not self.cache.mirror_exists(url):
            # Clone as bare repository
            self._run_git(
                ["clone", "--bare", "--mirror", "--", url, str(mirror_path)],
                cwd=self.cache.cache_dir,
            )

        return mirror_path

    def _fetch_mirror(self, mirror_path: Path, url: str) -> None:
        """Fetch latest from remote into mirror.

        Args:
            mirror_path: Path to mirror repository
            url: Remote URL to fetch from
        """
        self._run_git(
            [
                "fetch",
                "--prune",
                "--",
                url,
                "+refs/heads/*:refs/heads/*",
                "+refs/tags/*:refs/tags/*",
            ],
            cwd=mirror_path,
        )

    def _resolve_ref(self, mirror_path: Path, ref: str) -> str:
        """Resolve ref to commit SHA.

        Args:
            mirror_path: Path to mirror repository
            ref: Git ref (branch, tag, commit)

        Returns:
            40-character commit SHA
        """
        result = self._run_git(
            ["rev-parse", "--verify", f"{ref}^{{commit}}"],
            cwd=mirror_path,
            capture_output=True,
        )
        return result.stdout.strip()

    def _checkout(
        self,
        mirror_path: Path,
        checkout_path: Path,
        commit: str,
        sparse: list[str] | None,
        *,
        force: bool = False,
    ) -> None:
        """Checkout vendor at specific commit.

        Args:
            mirror_path: Path to mirror repository
            checkout_path: Path to create checkout at
            commit: Commit SHA to checkout
            sparse: Optional sparse checkout paths
            force: Force checkout even if already at correct commit
        """
        resolved_repo_root = self.repo_root.resolve()
        resolved_checkout = checkout_path.resolve()
        if not resolved_checkout.is_relative_to(resolved_repo_root):
            raise VendorCheckoutError(
                f"Refusing to create checkout outside repo root: {resolved_checkout}"
            )

        # Check if already at correct commit (skip if not forced)
        if checkout_path.exists() and not force:
            try:
                result = self._run_git(
                    ["rev-parse", "HEAD"],
                    cwd=checkout_path,
                    capture_output=True,
                )
                current_commit = result.stdout.strip()
                if current_commit == commit:
                    # Already at correct commit
                    return
            except Exception:
                # If we can't check, proceed with checkout
                pass

        # Remove existing checkout if present
        if checkout_path.exists():
            if not force and (checkout_path / ".git").exists():
                try:
                    status = self._run_git(
                        ["status", "--porcelain"],
                        cwd=checkout_path,
                        capture_output=True,
                    )
                    if status.stdout.strip():
                        raise VendorCheckoutError(
                            "Refusing to remove vendor checkout with local modifications; "
                            f"re-run with --force to discard changes: {checkout_path}"
                        )
                except VendorCheckoutError:
                    raise
                except Exception:
                    # If we can't check for dirtiness, proceed with checkout.
                    pass

            import shutil
            logger.warning(
                "Removing existing vendor checkout at %s to sync to commit %s",
                checkout_path,
                commit[:12],
            )
            shutil.rmtree(checkout_path)

        # Clone from mirror
        checkout_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_git(
            ["clone", "--no-checkout", "--", str(mirror_path), str(checkout_path)],
            cwd=checkout_path.parent,
        )

        # Configure sparse checkout if needed
        if sparse:
            self._run_git(["sparse-checkout", "init", "--cone"], cwd=checkout_path)
            self._run_git(["sparse-checkout", "set", "--"] + sparse, cwd=checkout_path)

        # Checkout specific commit
        self._run_git(["checkout", commit], cwd=checkout_path)

    def _run_git(
        self,
        args: list[str],
        cwd: Path,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run git command.

        Args:
            args: Git command arguments
            cwd: Working directory
            capture_output: Whether to capture output

        Returns:
            CompletedProcess result

        Raises:
            VendorCheckoutError: If git command fails
        """
        try:
            # Vendor checkout is a legitimate use of git checkout/clone/fetch.
            # Allow destructive git commands in vendor subprocess calls since
            # these operate on isolated vendor directories, not the main project.
            env = os.environ.copy()
            env["EDISON_ALLOW_DESTRUCTIVE_GIT"] = "1"

            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=True,
                env=env,
            )
            return result
        except subprocess.CalledProcessError as e:
            safe_cmd = "git " + " ".join(redact_git_args(args))
            safe_output = redact_text_credentials(e.stderr or e.stdout or str(e))
            raise VendorCheckoutError(
                f"Git command failed: {safe_cmd}\n{safe_output}"
            ) from e


__all__ = ["VendorCheckout"]
