"""Test-only extraction helpers mirroring the prose scanners in code_command.py and
patch_command.py (`#### Step N:`) and the Deferred Risk Register format shared with
task_planner.py. These are not production code — the real scanners live inside prompt
templates and cannot be executed directly (testing.md) — but the algorithm they
describe is concrete enough to reimplement once here so both the format-authoring test
(this phase) and any future consumer (Phase 6 code_command.py rewiring) share one
definition of "readable."
"""

import re
from dataclasses import dataclass


_STEP_HEADER = re.compile(r'^#### Step (\d+):\s*(.*)$', re.MULTILINE)
_HEADING = re.compile(r'^(?P<level>#{1,6}) (?P<name>.+?)\s*$')
_CHECKLIST_ITEM = re.compile(r'^\s*- \[[ xX]\] ')
_STEP_REFERENCE = re.compile(r'\(Step (\d+)\)')
_VERIFY_OPEN = '(verify:'
_DEFERRED_RISK = re.compile(
    r'^- (DR-\d+) \| status=(\w+) \| severity=(P[0-3]) \| scope=([\w-]+) \| reason=(.+)$',
    re.MULTILINE,
)


def extract_steps(markdown: str) -> list[str]:
    return [m.group(1) for m in _STEP_HEADER.finditer(markdown)]


def extract_deferred_risks(markdown: str) -> list[str]:
    return [m.group(1) for m in _DEFERRED_RISK.finditer(markdown)]


@dataclass(frozen=True)
class ChecklistItem:
    steps: list[str]
    verify: list[str]


def extract_h2_names(markdown: str) -> list[str]:
    headings = (_HEADING.match(line) for line in markdown.splitlines())
    return [heading.group('name') for heading in headings if heading and heading.group('level') == '##']


def extract_section(markdown: str, *heading_path: str) -> str:
    path: list[str] = []
    body: list[str] = []
    capturing = False
    for line in markdown.splitlines():
        heading = _HEADING.match(line)
        if heading:
            depth = len(heading.group('level')) - 1
            if capturing and depth <= len(heading_path):
                break
            path = [*path[: max(depth - 1, 0)], heading.group('name')] if depth else []
            if not capturing and tuple(path) == heading_path:
                capturing = True
                continue
        if capturing:
            body.append(line)
    return '\n'.join(body)


def extract_checklist_items(markdown: str) -> list[ChecklistItem]:
    return [
        ChecklistItem(steps=_STEP_REFERENCE.findall(line), verify=_verify_values(line))
        for line in markdown.splitlines()
        if _CHECKLIST_ITEM.match(line)
    ]


def _verify_values(item: str) -> list[str]:
    values: list[str] = []
    start = item.find(_VERIFY_OPEN)
    while start != -1:
        depth, end = 1, start + len(_VERIFY_OPEN)
        while end < len(item) and depth:
            depth += {'(': 1, ')': -1}.get(item[end], 0)
            end += 1
        if depth:
            return values
        values.append(item[start + len(_VERIFY_OPEN) : end - 1].strip())
        start = item.find(_VERIFY_OPEN, end)
    return values
