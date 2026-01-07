from __future__ import annotations

from pathlib import Path

from edison.core.components.service import ComponentService
from edison.core.composition.registries.agent_prompts import AgentPromptRegistry
from edison.core.config import ConfigManager


def _read_cfg(repo_root: Path) -> dict:
    return ConfigManager(repo_root=repo_root).load_config(validate=False, include_packs=True)


def test_component_service_enables_and_disables_pack(isolated_project_env: Path) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    svc.disable("pack", "react")
    cfg = _read_cfg(isolated_project_env)
    assert "react" not in ((cfg.get("packs") or {}).get("active") or [])

    svc.enable("pack", "react")
    cfg2 = _read_cfg(isolated_project_env)
    assert "react" in ((cfg2.get("packs") or {}).get("active") or [])


def test_component_service_toggles_validator_enabled_flag(isolated_project_env: Path) -> None:
    svc = ComponentService(repo_root=isolated_project_env)
    validator_id = "security"

    svc.disable("validator", validator_id)
    cfg = _read_cfg(isolated_project_env)
    vcfg = ((cfg.get("validation") or {}).get("validators") or {}).get(validator_id) or {}
    assert vcfg.get("enabled") is False

    svc.enable("validator", validator_id)
    cfg2 = _read_cfg(isolated_project_env)
    vcfg2 = ((cfg2.get("validation") or {}).get("validators") or {}).get(validator_id) or {}
    assert vcfg2.get("enabled") is True


def test_component_service_toggles_adapter_enabled_flag(isolated_project_env: Path) -> None:
    svc = ComponentService(repo_root=isolated_project_env)
    adapter_id = "codex"

    svc.enable("adapter", adapter_id)
    cfg = _read_cfg(isolated_project_env)
    adapters = (cfg.get("composition") or {}).get("adapters") or {}
    assert (adapters.get(adapter_id) or {}).get("enabled") is True

    svc.disable("adapter", adapter_id)
    cfg2 = _read_cfg(isolated_project_env)
    adapters2 = (cfg2.get("composition") or {}).get("adapters") or {}
    assert (adapters2.get(adapter_id) or {}).get("enabled") is False


def test_component_service_disables_agent_via_agents_config(isolated_project_env: Path) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    agent_id = "feature-implementer"
    assert agent_id in AgentPromptRegistry(project_root=isolated_project_env).list_names()

    svc.disable("agent", agent_id)
    reg = AgentPromptRegistry(project_root=isolated_project_env)
    assert agent_id not in reg.list_names()

    svc.enable("agent", agent_id)
    reg2 = AgentPromptRegistry(project_root=isolated_project_env)
    assert agent_id in reg2.list_names()


def test_component_service_configure_pack_writes_pack_config(isolated_project_env: Path) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    svc.enable("pack", "typescript")
    svc.configure(
        "pack",
        "typescript",
        interactive=False,
        provided_answers={
            "typescript_strict": False,
            "typescript_target": "ES2022",
            "typescript_module": "esnext",
        },
        mode="advanced",
    )

    cfg = _read_cfg(isolated_project_env)
    pack_cfg = (cfg.get("pack_config") or {}).get("typescript") or {}
    assert pack_cfg.get("strict") is False
    assert pack_cfg.get("target") == "ES2022"
    assert pack_cfg.get("module") == "esnext"


def test_component_service_configure_validator_applies_setup_template(
    isolated_project_env: Path,
) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    (isolated_project_env / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        """
validation:
  validators:
    demo-web:
      name: "Demo Web Validator"
      engine: pal-mcp
      wave: comprehensive
      enabled: true
      setup:
        require:
          config:
            - "validation.validators.demo-web.web_server.url"
        questions:
          - id: demo_web_url
            prompt: "Demo URL"
            type: string
            required: true
        config_template:
          validation:
            validators:
              demo-web:
                web_server:
                  url: "{{ demo_web_url }}"
""".lstrip(),
        encoding="utf-8",
    )

    svc.configure(
        "validator",
        "demo-web",
        interactive=False,
        provided_answers={"demo_web_url": "http://127.0.0.1:4242"},
        mode="basic",
    )

    cfg = _read_cfg(isolated_project_env)
    url = (
        (((cfg.get("validation") or {}).get("validators") or {}).get("demo-web") or {})
        .get("web_server", {})
        .get("url")
    )
    assert url == "http://127.0.0.1:4242"


def test_component_service_configure_pack_validator_writes_web_server_config(
    isolated_project_env: Path,
) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    svc.enable("pack", "e2e-web")

    status = svc.get_status("validator", "browser-e2e")
    assert "validation.web_servers.browser-e2e.url" in status.missing_required_config

    svc.configure(
        "validator",
        "browser-e2e",
        interactive=False,
        provided_answers={
            "e2e_web_url": "http://127.0.0.1:3000",
            "e2e_web_healthcheck_url": "http://127.0.0.1:3000/health",
            "e2e_web_ensure_running": True,
            "e2e_web_start_command": "pnpm dev --port 3000",
            "e2e_web_stop_after": True,
        },
        mode="advanced",
    )

    cfg = _read_cfg(isolated_project_env)
    validation = cfg.get("validation") or {}
    servers = (validation.get("web_servers") or {}) if isinstance(validation, dict) else {}
    profile = (servers.get("browser-e2e") or {}) if isinstance(servers, dict) else {}
    assert profile.get("url") == "http://127.0.0.1:3000"
    assert profile.get("healthcheck_url") == "http://127.0.0.1:3000/health"
    assert profile.get("ensure_running") is True
    assert (profile.get("start") or {}).get("command") == "pnpm dev --port 3000"
    assert profile.get("stop_after") is True

    entry = (validation.get("validators") or {}).get("browser-e2e") or {}
    web = (entry.get("web_server") or {}) if isinstance(entry, dict) else {}
    assert web.get("ref") == "browser-e2e"


def test_component_service_configure_validator_installs_script_templates(
    isolated_project_env: Path,
) -> None:
    svc = ComponentService(repo_root=isolated_project_env)

    (isolated_project_env / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        """
validation:
  validators:
    demo-web:
      name: "Demo Web Validator"
      engine: pal-mcp
      wave: comprehensive
      enabled: true
      setup:
        questions: []
        config_template:
          validation:
            validators:
              demo-web:
                web_server:
                  url: "http://127.0.0.1:4242"
        templates:
          - src: "web-server/start-server.sh"
            dest: ".edison/scripts/start-server.sh"
            executable: true
""".lstrip(),
        encoding="utf-8",
    )

    written = svc.configure(
        "validator",
        "demo-web",
        interactive=False,
        provided_answers={},
        mode="basic",
    )

    dest = isolated_project_env / ".edison" / "scripts" / "start-server.sh"
    assert dest.exists() is True
    assert "Edison" in dest.read_text(encoding="utf-8")
    assert dest in written
