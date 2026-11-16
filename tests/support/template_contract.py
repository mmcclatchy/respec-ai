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

# Claude Code tools a template names in prose ("Use AskUserQuestion tool to present
# options:") rather than calling as Name(...), so the call pattern above misses them (F12).
# opencode's `question` is too common a word to match here; B6 checks that TUI directly.
_BARE_TOOL_NAME_PATTERN = re.compile(r'\b(AskUserQuestion|SendMessage)\b')

_STEP_HEADER_PATTERN = re.compile(r'^#{2,4} Step (?P<number>\d+(?:\.\d+)*)\b')

_DECLARED_INPUT_PATTERN = re.compile(r'^- (\w+):')

# README "Subagent report format": the final message of every respec-phase-* subagent.
REPORT_HEADINGS = ('## For the user', '## Decisions needed', '## Research proposals', '## Status')
_GUARD_HEADER_PATTERN = re.compile(r'^\s*(?:IF|ELIF|ELSE)\b')

# Matches `IF <VAR>_DECISION == "VALUE":` / `ELIF <VAR>_DECISION == "VALUE":` branch
# headers. The variable name is captured so a branch lookup only treats same-named
# decision variables as sibling boundaries -- independently named decision chains
# must not collide.
_BRANCH_HEADER_PATTERN = re.compile(
    r'^(?P<indent>[ \t]*)(?:IF|ELIF)\s+(?P<var>\w*DECISION\w*)\s*==\s*"(?P<value>[^"]+)"',
    re.IGNORECASE,
)

# Matches the critic's existing `[<Name> - BLOCKING]` convention (see phase_critic.py,
# e.g. "[Research Path Invalid - BLOCKING]"), with or without surrounding `**`.
_BLOCKER_CONDITION_PATTERN = re.compile(r'\[([^\[\]]+?)\s*-\s*BLOCKING\]', re.IGNORECASE)

# README "Critic findings": every finding opens with its classification tag, then its marker.
_MECHANICAL_FINDING_PATTERN = re.compile(r'\[mechanical\]\s*\[([^\[\]]+?)\s*-\s*BLOCKING\]', re.IGNORECASE)
_JUDGMENT_FINDING_PATTERN = re.compile(r'\[judgment\]\s*\[([^\[\]]+?)\]', re.IGNORECASE)


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.strip().lower()).strip('-')


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip())


def _enclosing_lines(preceding_lines: list[str], indentation: int) -> tuple[str, ...]:
    enclosing: list[str] = []
    for line in reversed(preceding_lines):
        if not line.strip() or _indentation(line) >= indentation:
            continue
        indentation = _indentation(line)
        enclosing.append(line.strip())
        if indentation == 0:
            break
    return tuple(enclosing)


def _enclosing_guards(preceding_lines: list[str], indentation: int) -> tuple[str, ...]:
    return tuple(line for line in _enclosing_lines(preceding_lines, indentation) if _GUARD_HEADER_PATTERN.match(line))


def _own_block(following_lines: list[str], indentation: int) -> list[str]:
    block: list[str] = []
    for line in following_lines:
        if line.strip() and _indentation(line) <= indentation:
            break
        block.append(line)
    return block


def _is_within(number: str, section_number: str) -> bool:
    return number == section_number or number.startswith(f'{section_number}.')


@dataclass(frozen=True)
class WaitSite:
    step: str | None
    line: str
    guards: tuple[str, ...]

    @property
    def guarded(self) -> bool:
        return bool(self.guards)

    @property
    def top_level_step(self) -> str | None:
        return self.step.split('.', 1)[0] if self.step else None


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
        invoked.update(m.group(1).lower() for m in _BARE_TOOL_NAME_PATTERN.finditer(self._template))
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

    def mechanical_findings(self) -> set[str]:
        return {_slugify(match.group(1)) for match in _MECHANICAL_FINDING_PATTERN.finditer(self._template)}

    def judgment_findings(self) -> set[str]:
        return {_slugify(match.group(1)) for match in _JUDGMENT_FINDING_PATTERN.finditer(self._template)}

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

    def wait_sites(self) -> list[WaitSite]:
        """Every `WAIT for` line, with its step number and the conditions enclosing it.

        A condition encloses a WAIT when it is an IF/ELIF/ELSE header found by walking up
        to lines of strictly smaller indentation, repeatedly, without leaving the WAIT's
        step. FOR/WHILE/REPEAT headers are loops, not conditions. Guards are listed
        innermost first.
        """
        lines = self._template.split('\n')
        sites: list[WaitSite] = []
        step: str | None = None
        step_start = 0
        for index, line in enumerate(lines):
            header = _STEP_HEADER_PATTERN.match(line)
            if header:
                step, step_start = header.group('number'), index
            elif 'WAIT for' in line:
                guards = _enclosing_guards(lines[step_start:index], _indentation(line))
                sites.append(WaitSite(step=step, line=line.strip(), guards=guards))
        return sites

    def declared_inputs(self, heading: str) -> set[str]:
        lines = self._template.split('\n')
        if heading not in lines:
            return set()
        names: set[str] = set()
        for line in lines[lines.index(heading) + 1 :]:
            if line.startswith('#'):
                break
            if match := _DECLARED_INPUT_PATTERN.match(line):
                names.add(match.group(1))
        return names

    def report_format(self) -> list[str]:
        block: list[str] | None = None
        for line in self._template.split('\n'):
            stripped = line.strip()
            if not stripped.startswith('```'):
                if block is not None:
                    block.append(stripped)
                continue
            if block is None:
                block = []
            elif next((entry for entry in block if entry), '') == REPORT_HEADINGS[0]:
                return block
            else:
                block = None
        return []

    def report_section(self, heading: str) -> list[str]:
        section: list[str] = []
        inside = False
        for line in self.report_format():
            if line.startswith('## '):
                inside = line == heading
            elif inside and line:
                section.append(line)
        return section

    def guards_for(self, marker: str) -> list[tuple[str, ...]]:
        lines = self._template.split('\n')
        found: list[tuple[str, ...]] = []
        step_start = 0
        for index, line in enumerate(lines):
            if _STEP_HEADER_PATTERN.match(line):
                step_start = index
            elif marker in line:
                found.append(_enclosing_guards(lines[step_start:index], _indentation(line)))
        return found

    def touchpoint_steps(self) -> list[str]:
        return [
            header.group('number')
            for line in self._template.split('\n')
            if (header := _STEP_HEADER_PATTERN.match(line)) and 'TOUCHPOINT' in line
        ]

    def step_numbers(self) -> list[str]:
        return [
            header.group('number')
            for line in self._template.split('\n')
            if (header := _STEP_HEADER_PATTERN.match(line))
        ]

    def preamble(self) -> str:
        lines = self._template.split('\n')
        first_step = next((i for i, line in enumerate(lines) if _STEP_HEADER_PATTERN.match(line)), len(lines))
        return '\n'.join(lines[:first_step])

    def step_section(self, number: str) -> str:
        """Text under a step heading, its sub-steps included, or '' when no such step exists.

        Unlike step_body(), which stops at the next heading of any depth, this runs to the
        next heading that is neither this step nor one of its sub-steps (Step 11 spans
        11.1, 11.2, ... but not 12).
        """
        lines = self._template.split('\n')
        section: list[str] | None = None
        for line in lines:
            header = _STEP_HEADER_PATTERN.match(line)
            if section is None:
                if header and header.group('number') == number:
                    section = []
                continue
            if header and not _is_within(header.group('number'), number):
                break
            section.append(line)
        return '\n'.join(section) if section is not None else ''

    def line_steps(self) -> list[str | None]:
        steps: list[str | None] = []
        step: str | None = None
        for line in self._template.split('\n'):
            if header := _STEP_HEADER_PATTERN.match(line):
                step = header.group('number')
            steps.append(step)
        return steps

    def enclosing_at(self, index: int) -> tuple[str, ...]:
        lines = self._template.split('\n')
        step_start = next((i for i in range(index, -1, -1) if _STEP_HEADER_PATTERN.match(lines[i])), 0)
        return _enclosing_lines(lines[step_start:index], _indentation(lines[index]))

    def guards_at(self, index: int) -> tuple[str, ...]:
        return tuple(line for line in self.enclosing_at(index) if _GUARD_HEADER_PATTERN.match(line))

    def block_sites(self, block: str) -> list[int]:
        """Line indices where a multi-line block starts, compared line by line with indentation ignored.

        Adapter-rendered invocations are multi-line; a template may indent them as a unit
        (textwrap.indent) or substitute them as-is, and both must count as the block.
        """
        if not block.strip():
            return []
        wanted = [line.strip() for line in block.strip('\n').split('\n')]
        stripped = [line.strip() for line in self._template.split('\n')]
        return [
            index for index in range(len(stripped) - len(wanted) + 1) if stripped[index : index + len(wanted)] == wanted
        ]

    def decision_blocks(self, value: str) -> list[str]:
        """Each `IF/ELIF <VAR>DECISION == "value"` header with only the lines indented beneath it.

        decision_branch() runs to the next sibling branch, so a branch that ends a chain
        also takes in whatever follows it; this stops at the header's own indentation.
        """
        lines = self._template.split('\n')
        blocks: list[str] = []
        for index, line in enumerate(lines):
            header = _BRANCH_HEADER_PATTERN.match(line)
            if header and header.group('value').lower() == value.lower():
                own = _own_block(lines[index + 1 :], len(header.group('indent')))
                blocks.append('\n'.join([line, *own]).rstrip())
        return blocks


def template_contract(template: str) -> TemplateContract:
    return TemplateContract(template)
