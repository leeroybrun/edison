#!/usr/bin/env python3
"""Token counting utilities using tiktoken for accurate context measurement.

This module provides accurate token counting for all file types in the .agents/
directory structure, matching the actual tokenization used by LLMs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("⚠️  tiktoken not installed. Using fallback estimation (less accurate).")
    print("   Install with: python3 -m pip install --user tiktoken --break-system-packages")


class TokenCounter:
    """Token counter with tiktoken support and fallback estimation."""

    def __init__(self, model: str = "gpt-4"):
        """Initialize token counter.

        Args:
            model: Model name for tokenization (gpt-4, gpt-3.5-turbo, claude-3-sonnet)
        """
        self.model = model

        if TIKTOKEN_AVAILABLE:
            # Use cl100k_base for GPT-4/Claude (similar tokenization)
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.use_tiktoken = True
        else:
            # Fallback to estimation
            self.encoding = None
            self.use_tiktoken = False

    def count_text(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to tokenize

        Returns:
            Token count (accurate if tiktoken available, estimated otherwise)
        """
        if not text:
            return 0

        if self.use_tiktoken:
            return len(self.encoding.encode(text))
        else:
            # Fallback: estimate ~4 chars per token (industry standard heuristic)
            # This is reasonably accurate for English text
            # More sophisticated: count words and punctuation
            words = len(text.split())
            chars = len(text)
            # Average of word-based (1.3 tokens/word) and char-based (4 chars/token)
            return int((words * 1.3 + chars / 4) / 2)

    def count_file(self, file_path: Union[str, Path]) -> Dict[str, Union[int, str]]:
        """Count tokens in a file.

        Args:
            file_path: Path to file

        Returns:
            Dict with file info and token count
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                "file": str(file_path),
                "exists": False,
                "tokens": 0,
                "lines": 0,
                "chars": 0,
            }

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary file, skip
            return {
                "file": str(file_path),
                "exists": True,
                "binary": True,
                "tokens": 0,
                "lines": 0,
                "chars": 0,
            }

        return {
            "file": str(file_path),
            "exists": True,
            "tokens": self.count_text(content),
            "lines": len(content.splitlines()),
            "chars": len(content),
            "size_kb": file_path.stat().st_size / 1024,
        }

    def count_files(self, file_paths: List[Union[str, Path]]) -> Dict[str, any]:
        """Count tokens across multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            Dict with aggregated stats
        """
        results = []
        total_tokens = 0
        total_lines = 0
        total_chars = 0

        for fp in file_paths:
            info = self.count_file(fp)
            results.append(info)
            total_tokens += info.get("tokens", 0)
            total_lines += info.get("lines", 0)
            total_chars += info.get("chars", 0)

        return {
            "files": results,
            "total_files": len(file_paths),
            "total_tokens": total_tokens,
            "total_lines": total_lines,
            "total_chars": total_chars,
            "avg_tokens_per_file": total_tokens / len(file_paths) if file_paths else 0,
        }

    def count_directory(
        self,
        dir_path: Union[str, Path],
        pattern: str = "**/*",
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """Count tokens in all files in a directory.

        Args:
            dir_path: Directory path
            pattern: Glob pattern for files (default: all files)
            exclude_patterns: Patterns to exclude

        Returns:
            Dict with directory stats
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            return {
                "directory": str(dir_path),
                "exists": False,
                "total_tokens": 0,
            }

        exclude_patterns = exclude_patterns or []
        files = []

        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            # Check exclusions
            skip = False
            for exclude in exclude_patterns:
                if exclude in str(file_path):
                    skip = True
                    break

            if not skip:
                files.append(file_path)

        results = self.count_files(files)
        results["directory"] = str(dir_path)
        results["pattern"] = pattern

        return results

    def count_json_structure(self, json_path: Union[str, Path]) -> Dict[str, any]:
        """Count tokens in a JSON file with structure breakdown.

        Args:
            json_path: Path to JSON file

        Returns:
            Dict with detailed JSON token breakdown
        """
        json_path = Path(json_path)

        if not json_path.exists():
            return {
                "file": str(json_path),
                "exists": False,
                "total_tokens": 0,
            }

        content = json_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Count total
        total_tokens = self.count_text(content)

        # Try to break down by top-level keys
        breakdown = {}
        if isinstance(data, dict):
            for key, value in data.items():
                key_content = json.dumps({key: value}, indent=2)
                breakdown[key] = {
                    "tokens": self.count_text(key_content),
                    "percentage": 0,  # Will calculate after
                }

        # Calculate percentages
        for key in breakdown:
            breakdown[key]["percentage"] = (
                breakdown[key]["tokens"] / total_tokens * 100 if total_tokens > 0 else 0
            )

        return {
            "file": str(json_path),
            "exists": True,
            "total_tokens": total_tokens,
            "lines": len(content.splitlines()),
            "breakdown": breakdown,
        }


def count_tokens(text_or_file: Union[str, Path]) -> int:
    """Quick helper to count tokens.

    Args:
        text_or_file: Text string or file path

    Returns:
        Token count
    """
    counter = TokenCounter()

    # Check if it's a file path
    if isinstance(text_or_file, (str, Path)):
        path = Path(text_or_file)
        if path.exists() and path.is_file():
            result = counter.count_file(path)
            return result.get("tokens", 0)

    # Treat as text
    return counter.count_text(str(text_or_file))


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python token_counter.py <file_or_directory>")
        sys.exit(1)

    target = Path(sys.argv[1])
    counter = TokenCounter()

    if target.is_file():
        result = counter.count_file(target)
        print(f"\n📄 File: {result['file']}")
        print(f"   Tokens: {result['tokens']:,}")
        print(f"   Lines:  {result['lines']:,}")
        print(f"   Size:   {result.get('size_kb', 0):.2f} KB")
    elif target.is_dir():
        result = counter.count_directory(target, pattern="**/*.md")
        print(f"\n📁 Directory: {result['directory']}")
        print(f"   Total tokens: {result['total_tokens']:,}")
        print(f"   Total files:  {result['total_files']}")
        print(f"   Avg tokens:   {result['avg_tokens_per_file']:.0f}")
    else:
        print(f"❌ Not found: {target}")
        sys.exit(1)
