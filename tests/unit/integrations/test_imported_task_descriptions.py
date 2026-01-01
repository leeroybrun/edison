from pathlib import Path


def test_speckit_description_uses_real_relative_feature_path(tmp_path):
    from edison.core.import_.speckit import SpecKitFeature, SpecKitTask, generate_task_description

    project_root = tmp_path / "proj"
    project_root.mkdir()

    feature_dir = project_root / "my-specs" / "auth"
    feature_dir.mkdir(parents=True)

    feature = SpecKitFeature(
        name="auth",
        path=feature_dir,
        tasks=[],
        has_spec=True,
        has_plan=True,
        has_data_model=True,
        has_contracts=True,
    )
    task = SpecKitTask(id="T001", description="Do thing", phase="setup")

    desc = generate_task_description(task, feature, project_root=project_root)
    assert "**SpecKit Source**:" in desc
    assert "`my-specs/auth/tasks.md`" in desc


def test_openspec_description_includes_design_md_when_present(tmp_path):
    from edison.core.import_.openspec import OpenSpecChange, _render_task_description

    project_root = tmp_path / "proj"
    project_root.mkdir()

    change_dir = project_root / "openspec" / "changes" / "add-thing"
    change_dir.mkdir(parents=True)
    proposal = change_dir / "proposal.md"
    proposal.write_text("# Add thing\n", encoding="utf-8")
    design = change_dir / "design.md"
    design.write_text("# Design\n", encoding="utf-8")

    change = OpenSpecChange(
        change_id="add-thing",
        change_dir=change_dir,
        proposal_path=proposal,
        tasks_path=change_dir / "tasks.md",
        specs_dir=change_dir / "specs",
        design_path=design,
    )

    desc = _render_task_description(change, project_root=project_root)
    assert "- `openspec/changes/add-thing/design.md`" in desc

