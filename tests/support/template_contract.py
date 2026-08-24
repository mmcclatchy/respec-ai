"""Test-only helper for asserting semantic structure of generated command templates.

Templates are prompts, not executable code, so ordinary string assertions break on
rewording and pass on genuinely broken output. This module extracts a small semantic
contract (decision branches, tool declarations vs. invocations) so tests can assert
against structure instead of prose. No production code imports this module.
"""

import re
from dataclasses import dataclass

_ALLOWED_TOOLS_LINE = re.compile(r'^allowed-tools:\s*(.+)$', re.MULTILINE)
_MCP_TOOL_PATTERN = re.compile(r'\bmcp__[\w-]+__\w+')
_BUILTIN_CALL_PATTERN = re.compile(r'\b(Read|Write|Glob|Bash|Grep|Task)\(')

# Matches `IF <VAR>_DECISION == "VALUE":` / `ELIF <VAR>_DECISION == "VALUE":` branch
# headers. The variable name is captured so a branch lookup only treats same-named
# decision variables as sibling boundaries -- Step 7's LOOP_DECISION chain and Step
# 7.6's independently named POST_SYNTHESIS_DECISION chain must not collide.
_BRANCH_HEADER_PATTERN = re.compile(
    r'^(?P<indent>[ \t]*)(?:IF|ELIF)\s+(?P<var>\w*DECISION\w*)\s*==\s*"(?P<value>[^"]+)"',
    re.IGNORECASE,
)

# Matches the critic's existing `[<Name> - BLOCKING]` convention (see phase_critic.py,
# e.g. "[Research Path Invalid - BLOCKING]"), with or without surrounding `**`.
_BLOCKER_CONDITION_PATTERN = re.compile(r'\[([^\[\]]+?)\s*-\s*BLOCKING\]', re.IGNORECASE)


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.strip().lower()).strip('-')


@dataclass
class DecisionBranch:
    value: str
    body: str

    def blocks_for_user_response(self) -> bool:
        return 'WAIT for' in self.body

    def persists_user_feedback(self) -> bool:
        return 'store_user_feedback' in self.body


class TemplateContract:
    def __init__(self, template: str) -> None:
        self._template = template

    def declared_tools(self) -> set[str]:
        match = _ALLOWED_TOOLS_LINE.search(self._template)
        if not match:
            return set()
        return {raw.strip().split('(', 1)[0].lower() for raw in match.group(1).split(',') if raw.strip()}

    def invoked_tools(self) -> set[str]:
        # Lowercased so a builtin capability invoked with the generic name used in prose
        # (e.g. "Read(...)") still matches its declaration under an adapter that renders
        # built-in tool names differently-cased (e.g. OpenCode's "read").
        invoked = {m.group(0).lower() for m in _MCP_TOOL_PATTERN.finditer(self._template)}
        invoked.update(m.group(1).lower() for m in _BUILTIN_CALL_PATTERN.finditer(self._template))
        return invoked

    def decision_branch(self, value: str) -> DecisionBranch:
        lines = self._template.split('\n')
        for i, line in enumerate(lines):
            header = _BRANCH_HEADER_PATTERN.match(line)
            if not header or header.group('value').lower() != value.lower():
                continue

            indent = len(header.group('indent'))
            variable = header.group('var')
            body_lines: list[str] = []
            for follow_line in lines[i + 1 :]:
                sibling = _BRANCH_HEADER_PATTERN.match(follow_line)
                if sibling and sibling.group('var') == variable and len(sibling.group('indent')) <= indent:
                    break
                body_lines.append(follow_line)

            return DecisionBranch(value=value, body='\n'.join(body_lines))

        raise ValueError(f'No decision branch found for value {value!r}')

    def blocker_conditions(self) -> set[str]:
        return {_slugify(match.group(1)) for match in _BLOCKER_CONDITION_PATTERN.finditer(self._template)}

    def step_body(self, step_number: str) -> str:
        """Text between a `### Step N:`/`#### Step N:` header and the next Step header.

        Anchored on the step number, not the title, so it survives retitling. Legitimate
        per testing.md: downstream code (code_command.py) actually scans `#### Step N:`,
        so the number is part of the contract, not incidental prose.
        """
        header = re.search(rf'^#{{2,4}} Step {re.escape(step_number)}:.*$', self._template, re.MULTILINE)
        if not header:
            raise ValueError(f'No Step {step_number} header found')

        start = header.end()
        next_header = re.search(r'^#{2,4} Step \d', self._template[start:], re.MULTILINE)
        end = start + next_header.start() if next_header else len(self._template)
        return self._template[start:end]

    def outcome_condition(self, body: str, outcome_marker: str) -> str:
        """The nearest preceding IF/ELIF/ELSE line that guards a line containing marker.

        Lets a test assert *what must be true* for an outcome (e.g. "Proceed to Step
        12") without depending on exact prose elsewhere in the branch body.
        """
        lines = body.split('\n')
        for i, line in enumerate(lines):
            if outcome_marker in line:
                for j in range(i, -1, -1):
                    if re.match(r'^\s*(IF|ELIF|ELSE)\b', lines[j]):
                        return lines[j].strip()
                raise ValueError(f'Marker {outcome_marker!r} found but no guarding IF/ELIF/ELSE above it')

        raise ValueError(f'No line containing {outcome_marker!r} found in body')

    def wait_prompt_count(self, body: str) -> int:
        return body.count('WAIT for')

    def resume_marker_count(self, body: str) -> int:
        return len(re.findall(r'resume at Step', body))


def template_contract(template: str) -> TemplateContract:
    return TemplateContract(template)
