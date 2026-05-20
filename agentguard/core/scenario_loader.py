"""Load and validate scenario YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from agentguard.core.errors import ScenarioLoadError
from agentguard.schemas.scenario import Scenario


def load_scenario(path: Path) -> Scenario:
    """Load and validate a single scenario YAML file."""
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise ScenarioLoadError(f"Failed to read {path}: {e}") from e
    if not isinstance(data, dict):
        raise ScenarioLoadError(f"{path}: top-level YAML must be a mapping")
    try:
        return Scenario(**data)
    except Exception as e:
        raise ScenarioLoadError(f"{path}: invalid scenario: {e}") from e


def load_scenarios(directory: Path) -> list[Scenario]:
    """Load all scenarios from a directory (recursive) or a single YAML file."""
    if directory.is_file():
        return [load_scenario(directory)]
    scenarios: list[Scenario] = []
    for yaml_file in sorted(directory.rglob("*.yaml")):
        scenarios.append(load_scenario(yaml_file))
    for yml_file in sorted(directory.rglob("*.yml")):
        scenarios.append(load_scenario(yml_file))
    return scenarios


def validate_scenario(scenario: Scenario) -> list[str]:
    """Return list of validation warnings/errors."""
    warnings: list[str] = []
    if scenario.agent.adapter == "http" and not scenario.agent.url:
        warnings.append(f"Scenario {scenario.id}: HTTP adapter requires 'url'")
    if scenario.agent.adapter in ("langgraph", "langchain", "openai_agents", "crewai") and (
        not scenario.agent.module or not scenario.agent.object
    ):
        warnings.append(
            f"Scenario {scenario.id}: {scenario.agent.adapter} adapter requires 'module' and 'object'"
        )
    if not scenario.metrics:
        warnings.append(f"Scenario {scenario.id}: No metrics specified")
    return warnings
