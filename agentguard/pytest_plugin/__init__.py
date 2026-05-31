"""AgentGuard pytest plugin (BLUEPRINT-7 section 5).

Registered via ``[project.entry-points."pytest11"] agentguard = "agentguard.pytest_plugin"``.
Three usage modes:

* ``@agentguard.scenario("path.yaml")`` - run a YAML scenario as a pytest test.
* ``@agentguard.suite("dir/")`` - parametrize across every scenario in a dir.
* ``@agentguard.inline_scenario(...)`` - build a Scenario in code and run it.
* Plus the trace-then-evaluate pattern with ``with agentguard.trace(): ...`` and
  ``agentguard.evaluate(t, ...)`` - works automatically with no plugin glue.

The plugin also adds the ``agentguard_trace`` fixture and the
``--agentguard-skip-llm-judge`` / ``--agentguard-fail-under`` /
``--agentguard-save-db`` / ``--agentguard-report=...`` command-line options.
"""

# Make decorators accessible under ``agentguard.<name>`` too
import agentguard as _ag
from agentguard.pytest_plugin.decorators import (
    inline_scenario,
    scenario,
    suite,
)
from agentguard.pytest_plugin.fixtures import agentguard_trace  # re-export for tests
from agentguard.pytest_plugin.hooks import (  # registered by pytest
    pytest_addoption,
    pytest_assertrepr_compare,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_sessionfinish,
)

_ag.scenario = scenario  # type: ignore[attr-defined]
_ag.suite = suite  # type: ignore[attr-defined]
_ag.inline_scenario = inline_scenario  # type: ignore[attr-defined]

__all__ = [
    "agentguard_trace",
    "inline_scenario",
    "pytest_addoption",
    "pytest_assertrepr_compare",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "pytest_sessionfinish",
    "scenario",
    "suite",
]
