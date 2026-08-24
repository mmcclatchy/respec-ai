"""Test-only extraction helpers mirroring the prose scanners in code_command.py and
patch_command.py (`#### Step N:`) and the Deferred Risk Register format shared with
task_planner.py. These are not production code — the real scanners live inside prompt
templates and cannot be executed directly (testing.md) — but the algorithm they
describe is concrete enough to reimplement once here so both the format-authoring test
(this phase) and any future consumer (Phase 6 code_command.py rewiring) share one
definition of "readable."
"""

import re

_STEP_HEADER = re.compile(r'^#### Step (\d+):\s*(.*)$', re.MULTILINE)
_DEFERRED_RISK = re.compile(
    r'^- (DR-\d+) \| status=(\w+) \| severity=(P[0-3]) \| scope=([\w-]+) \| reason=(.+)$',
    re.MULTILINE,
)


def extract_steps(markdown: str) -> list[str]:
    return [m.group(1) for m in _STEP_HEADER.finditer(markdown)]


def extract_deferred_risks(markdown: str) -> list[str]:
    return [m.group(1) for m in _DEFERRED_RISK.finditer(markdown)]
