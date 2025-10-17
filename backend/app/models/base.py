from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    slug: Mapped[str]
    description: Mapped[str | None]
    created_by: Mapped[str]
    settings_json: Mapped[dict] = mapped_column(default=dict)


class ProviderCredential(Base, TimestampMixin):
    __tablename__ = "provider_credential"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    provider: Mapped[str]
    label: Mapped[str]
    enc_key: Mapped[str]
    meta_json: Mapped[dict] = mapped_column(default=dict)


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str]
    description: Mapped[str | None]
    goal_text: Mapped[str]
    rubric_json: Mapped[dict]
    safety_json: Mapped[dict | None] = mapped_column(default=dict)
    selector_json: Mapped[dict | None] = mapped_column(default=dict)
    refiner_json: Mapped[dict | None] = mapped_column(default=dict)
    max_iterations: Mapped[int | None]
    budget_tokens: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="idle")


class Dataset(Base, TimestampMixin):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str]
    kind: Mapped[str]
    meta_json: Mapped[dict] = mapped_column(default=dict)


class Case(Base, TimestampMixin):
    __tablename__ = "case"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(index=True)
    input_json: Mapped[dict]
    expected_json: Mapped[dict | None] = mapped_column(default=dict)
    tags: Mapped[list[str]] = mapped_column(default=list)
    difficulty: Mapped[int | None]


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(index=True)
    parent_id: Mapped[int | None]
    text: Mapped[str]
    system_text: Mapped[str | None]
    shots_json: Mapped[list[dict] | None] = mapped_column(default=list)
    tools_schema_json: Mapped[dict | None] = mapped_column(default=dict)
    changelog: Mapped[str | None]
    created_by: Mapped[str | None]
    is_production: Mapped[bool] = mapped_column(default=False)


class ModelRun(Base, TimestampMixin):
    __tablename__ = "model_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_version_id: Mapped[int] = mapped_column(index=True)
    model_id: Mapped[str]
    params_json: Mapped[dict] = mapped_column(default=dict)
    seed: Mapped[int | None]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    token_in: Mapped[int | None]
    token_out: Mapped[int | None]
    cost_usd: Mapped[float | None]
    latency_ms: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="pending")


class Output(Base, TimestampMixin):
    __tablename__ = "output"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_run_id: Mapped[int] = mapped_column(index=True)
    case_id: Mapped[int] = mapped_column(index=True)
    raw_text: Mapped[str]
    content_json: Mapped[dict | None] = mapped_column(default=dict)
    tokens_out: Mapped[int | None]
    latency_ms: Mapped[int | None]
    meta_json: Mapped[dict] = mapped_column(default=dict)


class Judgment(Base, TimestampMixin):
    __tablename__ = "judgment"

    id: Mapped[int] = mapped_column(primary_key=True)
    output_id: Mapped[int] = mapped_column(index=True)
    judge_model_id: Mapped[str]
    mode: Mapped[str]
    scores_json: Mapped[dict] = mapped_column(default=dict)
    rationale_json: Mapped[dict] = mapped_column(default=dict)
    safety_json: Mapped[dict | None] = mapped_column(default=dict)
    winner_output_id: Mapped[int | None]


class Suggestion(Base, TimestampMixin):
    __tablename__ = "suggestion"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_version_id: Mapped[int] = mapped_column(index=True)
    source: Mapped[str]
    diff_unified: Mapped[str]
    note: Mapped[str]


class Iteration(Base, TimestampMixin):
    __tablename__ = "iteration"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(index=True)
    number: Mapped[int]
    selected_prompt_version_id: Mapped[int | None]
    metrics_json: Mapped[dict] = mapped_column(default=dict)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class Review(Base, TimestampMixin):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(index=True)
    output_id: Mapped[int | None]
    reviewer_id: Mapped[str]
    decision: Mapped[str]
    notes: Mapped[str | None]


class Job(Base, TimestampMixin):
    __tablename__ = "job"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    payload_json: Mapped[dict] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(default="pending")
    scheduled_at: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None]
    worker_id: Mapped[str | None]


class ExportBundle(Base, TimestampMixin):
    __tablename__ = "export_bundle"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(index=True)
    path: Mapped[str]
    checksum: Mapped[str]
