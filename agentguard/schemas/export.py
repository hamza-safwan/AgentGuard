"""Render the v1 JSON Schemas under ``schemas/v1/`` (BLUEPRINT-7 section 3.2).

The downstream JS / TS SDK consumes these schemas via
``json-schema-to-typescript`` to keep its types in lock-step with the Python
source of truth. Run via ``python -m agentguard.schemas.export``; CI then
asserts ``git diff --exit-code schemas/`` to catch drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentguard.schemas import (
    AgentTrace,
    EvaluationResult,
    RunSummary,
    Scenario,
    ScenarioResult,
    TraceStep,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas" / "v1"

EXPORTS: dict[str, type] = {
    "scenario.schema.json": Scenario,
    "trace_step.schema.json": TraceStep,
    "trace.schema.json": AgentTrace,
    "evaluation_result.schema.json": EvaluationResult,
    "scenario_result.schema.json": ScenarioResult,
    "run_summary.schema.json": RunSummary,
}


def export(out_dir: Path = SCHEMA_DIR) -> list[Path]:
    """Write all schemas to ``out_dir``. Returns the list of written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, model in EXPORTS.items():
        schema = model.model_json_schema()
        schema["$id"] = f"https://schemas.agentguard.dev/v1/{filename}"
        path = out_dir / filename
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> None:
    written = export()
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
