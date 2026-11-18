import re
import string
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from src.models.document_validation import (
    CitedPath,
    CitedPathKind,
    FindingOwner,
    StructuralCheck,
    StructuralFinding,
)
from src.models.phase import Phase
from src.utils.skeleton_types import BULLET_PATH, SkeletonIndexParseError, parse_bare_signature, strip_tags
from src.utils.state_manager.base import FROZEN_PHASES_FIELDS


SKELETON_INDEX_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['skeleton_index'])
TEST_LIST_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['test_list'])
OPEN_DECISIONS_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['open_design_decisions'])
SETTLED_DECISIONS_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['settled_design_decisions'])
UX_CONTRACT_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['design_shape_additional'])
RESEARCH_REQUIREMENTS_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['research_requirements'])
SUCCESS_CRITERIA_LOCATION = ' > '.join(Phase.HEADER_FIELD_MAPPING['success_criteria'])
RESERVED_H2_NAMES = frozenset(header_path[0] for header_path in Phase.HEADER_FIELD_MAPPING.values())
DESIGN_SHAPE_FIELDS = tuple(
    field_name for field_name, header_path in Phase.HEADER_FIELD_MAPPING.items() if header_path[0] == 'Design Shape'
)

GROUNDING, DELEGATION_BOUNDS, BEHAVIORS_AND_ACCEPTANCE, GUARDRAILS = Phase.BRIEF_SECTIONS
FINALIZER_SECTIONS = (GROUNDING, BEHAVIORS_AND_ACCEPTANCE, GUARDRAILS)
RESEARCH_TO_READ = 'Research to read'
REQUIRED_BRIEF_SUBSECTIONS: dict[str, tuple[str, ...]] = {
    GROUNDING: ('Build on', 'Leave alone', 'Exemplars', 'Conventions', RESEARCH_TO_READ),
    DELEGATION_BOUNDS: ('Out of scope', "Implementer's discretion", 'Escalate if'),
    BEHAVIORS_AND_ACCEPTANCE: ('Not covered by tests',),
    GUARDRAILS: ('Invariants', 'Error policy', 'Security and performance', 'Deviation protocol'),
}
GROUNDING_PATH_SUBSECTIONS: dict[str, str] = {
    name.casefold(): name for name in REQUIRED_BRIEF_SUBSECTIONS[GROUNDING] if name != RESEARCH_TO_READ
}

# Lines the architect cannot change: the frozen Overview is preserved by storage, and SD entries
# and the Research Requirements ledger are orchestrator-written history it carries forward verbatim.
REFERENCE_EXEMPT_FIELDS = frozenset({*FROZEN_PHASES_FIELDS, 'settled_design_decisions', 'research_requirements'})

SD_KEYS = frozenset(
    {'source', 'supersedes', 'decision', 'rationale', 'rejected', 'affects', 'binding', 'section', 'reason'}
)
DECIDED_FIELDS = ('decision', 'rationale', 'binding')
REQUIRED_SD_FIELDS: dict[str, tuple[str, ...]] = {
    'user': DECIDED_FIELDS,
    'user-menu': DECIDED_FIELDS,
    'user-override': DECIDED_FIELDS,
    'materializer': DECIDED_FIELDS,
    'architect': DECIDED_FIELDS,
    'user-edit': ('decision', 'binding'),
    'implementation': ('supersedes', 'reason'),
}
ORCHESTRATOR_SOURCES = frozenset({'user', 'user-edit', 'user-menu', 'user-override', 'materializer', 'implementation'})
ACCEPT_SOURCE = 'user'
ACCEPT_SUPERSEDES = 'unresolved-checks'
ID_FAMILIES = ('OD', 'SD', 'CQ', 'RP', 'FLOW')
BRIEF_ID_FAMILIES = ('T', 'SC', 'G')
SETTLED_BY_SUPERSEDES = frozenset({'OD', 'CQ'})
REQUIRED_OPTIONS = ('A', 'B')
ALLOWED_OPTIONS = frozenset({'A', 'B', 'C'})
TOKEN_PUNCTUATION = string.punctuation + '—–‘’“”'

IMPLEMENTATION_FILE = 'implementation.md'
BUILD_ORDER = 'Build Order'
STEPS = 'Steps'
CHECKLIST = 'Checklist'
POLICY = 'Policy'
STEPS_PART = f'{BUILD_ORDER} > {STEPS}'
REQUIRED_PLAN_PARTS = (STEPS_PART, CHECKLIST, POLICY)
POLICY_SUBSECTIONS = ('Execution Intent Policy', 'Deferred Risk Register')
START_HERE = 'Start here'
EXIT_CRITERIA = 'Exit criteria'
DEVIATIONS = 'Deviations'
FINALIZE_SECTIONS = (START_HERE, EXIT_CRITERIA, DEVIATIONS)
FINALIZE_SECTION_BY_FOLD: dict[str, str] = {name.casefold(): name for name in FINALIZE_SECTIONS}
START_HERE_SUBSECTIONS = ('Prerequisites', 'Required reading', 'First action')
DRAFT_FIELDS = ('Goal', 'Files', 'Depends on')
STEP_FIELDS = ('Goal', 'Context', 'Files', 'Depends on', 'Tests to turn green', 'Verify', 'Done when')
FINALIZE_FIELDS = tuple(label for label in STEP_FIELDS if label not in DRAFT_FIELDS)
STEP_FIELD_BY_FOLD: dict[str, str] = {label.casefold(): label for label in STEP_FIELDS}
ID_SCANNED_FIELDS = frozenset({'Context', 'Tests to turn green'})
FINALIZE_ONLY_SEGMENTS = frozenset(name.casefold() for name in (*FINALIZE_SECTIONS, *FINALIZE_FIELDS))
VERIFY_OPEN = '(verify:'
ASK_USER_MARKER = 'ask user'
BEST_PRACTICES_PREFIX = '.best-practices/'
INTERACTION_FLOWS = 'interaction flows'
INTERACTION_FLOWS_LEVEL = 5
# Settled entries are orchestrator-written history the architect carries forward verbatim, and an
# accept-as-is entry quotes the missing-path finding it accepts, so its paths are never re-verified.
CITATION_EXEMPT_FIELDS = frozenset({'settled_design_decisions'})

_FENCE = re.compile(r'^\s*(?P<run>`{3,}(?=[^`]*$)|~{3,})')
_BULLET = re.compile(r'^[-*+](?=\s|`|$)')
_NONE_MARKER = re.compile(r'^[-*+]\s+none\b', re.IGNORECASE)
_ID_TOKEN = re.compile(r'\b(?P<family>OD|SD|CQ|RP|FLOW)-(?P<number>[0-9]+)\b')
_OD_ENTRY = re.compile(r'^[-*+]\s+(?P<id>OD-(?P<number>[0-9]+))\b(?P<rest>.*)$')
_SD_ENTRY = re.compile(r'^[-*+]\s+(?P<id>SD-(?:(?P<number>[0-9]+)|###))(?P<rest>(?:[\s|].*)?)$')
_FLOW_DEFINITION = re.compile(r'^\s*[-*+]\s+(?P<id>FLOW-(?P<number>[0-9]+))\b')
_TITLE_PREFIX = re.compile(r'^title:', re.IGNORECASE)
_SINGLE_LINE_FORM = re.compile(r'\|\s*Option\s+[A-Za-z]\s*:|\bRecommended\s*:')
_OPTION_LINE = re.compile(r'^\s*[-*+]\s+Option\s+(?P<letter>[A-Za-z])\s*[:.)—–-](?P<text>.*)$')
_RECOMMENDED_LINE = re.compile(r'^\s*[-*+]\s+Recommended\b\s*[:—–-]?(?P<text>.*)$')
_SETTLES_OD_OR_CQ = re.compile(r'^(?:OD|CQ)-[0-9]+\b')
_STEP_HEADING = re.compile(r'^#### Step (?P<number>[0-9]+):(?P<title>.*)$')
_NUMBERED_STEP_HEADING = re.compile(r'^####\s+Step\s+(?P<number>[0-9]+)')
_CHECKLIST_ITEM = re.compile(r'^\s*[-*+]\s+\[[ xX]\]')
_STEP_REFERENCE = re.compile(r'\(Step (?P<number>[0-9]+)\)')
_PLACEHOLDER_COMMAND = re.compile(r'[\[<(]?\s*todo\b|no_preference$|<.*>$|\[.*\]$', re.IGNORECASE | re.DOTALL)
# An angle-bracket placeholder token such as <command>; never shell redirection like `cmd < in > out`.
_PLACEHOLDER_TOKEN = re.compile(r'<[A-Za-z](?:[^<>]*[^\s<>])?>')
_BRIEF_ID_TOKEN = re.compile(r'\b(?P<family>T|SC|G)-(?P<number>[0-9]+)\b')
_TRAILING_TEST_ID = re.compile(r'(?:^|\s)[—–-]\s*(?P<id>T-(?P<number>[0-9]+))\s*$')
_CRITERION_ENTRY = re.compile(r'^[-*+]\s+(?P<id>SC-(?P<number>[0-9]+))\s*:')
_GUARDRAIL_ENTRY = re.compile(r'^[-*+]\s+(?P<id>G-(?P<number>[0-9]+))\s*:')
_MEASURE = re.compile(r'\bmeasure\s*:', re.IGNORECASE)
_STEP_TOKEN = re.compile(r'\bStep (?P<number>[0-9]+)\b')
_AFFECTS_LINE = re.compile(r'^\s*[-*+]\s+Affects\s*:', re.IGNORECASE)
_STEP_FIELD = re.compile(
    r'^[-*+]\s+\*\*\s*(?P<label>' + '|'.join(re.escape(label) for label in STEP_FIELDS) + r')\s*(?::\*\*|\*\*\s*:)'
    r'(?P<value>.*)$',
    re.IGNORECASE,
)
_FILE_ITEM = re.compile(r'`(?P<path>[^`]+)`|\b(?P<verb>create|modify)\b|(?P<separator>;)', re.IGNORECASE)
_READ_LINE = re.compile(r'^\s*[-*+]\s+Read:\s*(?P<rest>.*)$')
_APPLIED_LINE = re.compile(r'^\s*[-*+]\s+Applied:')
_CONSTRAINT_LINE = re.compile(r'^\s*[-*+]\s+Constraint:\s*(?P<rest>.*)$')
_BACKTICK_SPAN = re.compile(r'`(?P<inner>[^`]+)`')
_MENTION_DELIMITERS = re.compile(r'[\s`"\'()\[\]{}<>‘’“”]+')
_MARKDOWN_SUFFIX = re.compile(r'\.md(?![\w-])')

SEAM_NOTATION = '<Owner>.<member>(<params>) -> <Result>'
DEFINED_BY: dict[str, str] = {
    'OD': 'entry in Open Design Decisions or SD supersedes= value',
    'SD': 'entry in Settled Design Decisions',
    'CQ': 'SD supersedes= value (CQ IDs live only in the critic report)',
    'RP': 'Research Requirements line',
    'FLOW': '- FLOW-<n>: bullet in the UX Contract',
    'T': 'Test List entry ending in — T-<n>',
    'SC': '- SC-<n>: entry in Success Criteria',
    'G': '- G-<n>: entry in Guardrails',
}
PLAN_SECTION_DETAILS: dict[str, str] = {
    STEPS_PART: (
        'implementation.md has no ## Build Order section with a ### Steps subsection; add it with one'
        ' #### Step <integer>: <title> heading per step.'
    ),
    CHECKLIST: (
        'implementation.md has no ## Checklist section; add it with one'
        ' - [ ] <item> (Step <integer>) (verify: <command>) line per step.'
    ),
    POLICY: (
        'implementation.md has no ## Policy section; add it with its ### Execution Intent Policy and'
        ' ### Deferred Risk Register subsections.'
    ),
}
FINALIZE_SECTION_DETAILS: dict[str, str] = {
    START_HERE: (
        'implementation.md has finalized content but no ## Start here section; add it with its ### Prerequisites,'
        ' ### Required reading and ### First action subsections.'
    ),
    EXIT_CRITERIA: (
        'implementation.md has finalized content but no ## Exit criteria section; add it, naming in backticks'
        ' each configured command that verifies the whole phase.'
    ),
    DEVIATIONS: (
        'implementation.md has finalized content but no ## Deviations section; add it holding - None until an'
        ' implementer records a deviation.'
    ),
}


@dataclass(frozen=True)
class _Section:
    location: str
    field_name: str
    text: str


@dataclass
class _OpenEntry:
    subject: str
    number: str
    head_parts: tuple[str, ...]
    checks_sub_lines: bool
    sub_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _SettledEntry:
    line: str
    written_id: str
    number: str
    values: dict[str, str]

    @property
    def subject(self) -> str:
        return self.written_id if self.number else self.line

    @property
    def source(self) -> str:
        return self.value('source').lower()

    @property
    def owner(self) -> FindingOwner:
        return FindingOwner.ORCHESTRATOR if self.source in ORCHESTRATOR_SOURCES else FindingOwner.ARCHITECT

    def value(self, key: str) -> str:
        return self.values.get(key, '').strip()


@dataclass(frozen=True)
class _Definition:
    family: str
    number: str
    written: str
    location: str
    owner: FindingOwner
    counts_for_duplicates: bool = True


@dataclass
class _IdIndex:
    resolvable: dict[str, set[str]]
    duplicates: list[StructuralFinding]
    settled_ods: set[str]


@dataclass
class _Step:
    written: str
    number: str
    fields: list[tuple[str, list[str]]] = field(default_factory=list)

    @property
    def subject(self) -> str:
        return f'Step {self.written}'

    @property
    def labels(self) -> list[str]:
        return [label for label, _ in self.fields]

    @property
    def is_finalized(self) -> bool:
        return set(STEP_FIELDS) <= set(self.labels)

    def location(self, label: str = '') -> str:
        return ' > '.join(part for part in (IMPLEMENTATION_FILE, self.subject, label) if part)

    def lines(self, label: str) -> list[str]:
        return [line for written, field_lines in self.fields if written == label for line in field_lines]


@dataclass
class _PlanPosition:
    h2: str = ''
    h3: str = ''
    step: _Step | None = None
    label: str = ''

    @property
    def location(self) -> str:
        if self.step is not None:
            return self.step.location(self.label)
        return ' > '.join(name for name in (IMPLEMENTATION_FILE, self.h2, self.h3) if name)


@dataclass
class _PlanScan:
    sections: set[str] = field(default_factory=set)
    steps: dict[str, str] = field(default_factory=dict)
    step_blocks: list[_Step] = field(default_factory=list)
    numbered_steps: set[str] = field(default_factory=set)
    has_malformed_heading: bool = False
    finalize_sections: set[str] = field(default_factory=set)
    subsections: dict[str, set[str]] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)
    exit_lines: list[str] = field(default_factory=list)
    references: list[tuple[str, str]] = field(default_factory=list)
    brief_references: list[tuple[str, str]] = field(default_factory=list)
    findings: list[StructuralFinding] = field(default_factory=list)


def check_phase_structure(phase: Phase) -> list[StructuralFinding]:
    open_entries = _open_entries(phase.open_design_decisions)
    settled_entries = _settled_entries(phase.settled_design_decisions)
    index = _id_index(phase, open_entries, settled_entries)
    seam_findings, valid_seams = _skeleton_index_findings(phase)
    overlapping = _overlapping_sections(phase)
    return _reported(
        [
            *seam_findings,
            *_test_list_findings(phase.test_list, valid_seams),
            *_test_id_findings(phase.test_list),
            *(finding for entry in open_entries for finding in _open_entry_findings(entry)),
            *(finding for entry in settled_entries for finding in _settled_entry_findings(entry)),
            *(_overlap_finding(name) for name in overlapping),
            *index.duplicates,
            *_still_open_findings(open_entries, index),
            *_dangling_findings(_phase_reference_lines(phase, overlapping), index, _ID_TOKEN),
            *_dangling_findings(_brief_reference_lines(phase, overlapping), index, _BRIEF_ID_TOKEN),
            *_delegation_bounds_findings(phase),
            *_finalizer_section_findings(phase),
            *_success_criteria_findings(phase),
            *_research_copy_findings(phase),
        ],
        finalized=_has_finalizer_section(phase),
    )


def extract_cited_paths(phase: Phase) -> list[CitedPath]:
    unique: dict[tuple[str, CitedPathKind, str], CitedPath] = {}
    for section in _sections(phase):
        if section.field_name in CITATION_EXEMPT_FIELDS:
            continue
        for citation in _section_citations(section):
            unique.setdefault((citation.path, citation.kind, citation.cited_in), citation)
    return list(unique.values())


def extract_implementation_paths(markdown: str) -> list[CitedPath]:
    unique: dict[tuple[str, CitedPathKind, str], CitedPath] = {}
    for step in _scan_plan(markdown).step_blocks:
        cited_in = step.location('Files')
        for path, kind in _file_items(step.lines('Files')):
            unique.setdefault((path, kind, cited_in), CitedPath(path=path, kind=kind, cited_in=cited_in))
    return list(unique.values())


def check_implementation_structure(markdown: str, phase: Phase) -> list[StructuralFinding]:
    scan = _scan_plan(markdown)
    index = _id_index(
        phase, _open_entries(phase.open_design_decisions), _settled_entries(phase.settled_design_decisions)
    )
    return _reported(
        [
            *_missing_plan_sections(scan),
            *_policy_subsection_findings(scan),
            *scan.findings,
            *_no_steps_findings(scan),
            *_contiguity_findings(scan),
            *(finding for step in scan.step_blocks for finding in _step_findings(step)),
            *_dependency_findings(scan),
            *_checklist_findings(scan),
            *_exit_criteria_findings(scan),
            *_finalize_section_findings(scan),
            *_dangling_findings(scan.references, index, _ID_TOKEN),
            *_dangling_findings(scan.brief_references, index, _BRIEF_ID_TOKEN),
            *_seam_coverage_findings(scan, phase),
            *_test_coverage_findings(scan, phase),
            *_phase_step_reference_findings(scan, phase),
        ]
    )


def drop_accepted_findings(
    findings: list[StructuralFinding], phase: Phase
) -> tuple[list[StructuralFinding], list[str]]:
    accept_lines = [
        entry.line
        for entry in _settled_entries(phase.settled_design_decisions)
        if entry.source == ACCEPT_SOURCE and entry.value('supersedes').lower() == ACCEPT_SUPERSEDES
    ]
    kept: list[StructuralFinding] = []
    accepted: list[str] = []
    for finding in findings:
        key = _finding_key(finding)
        if any(_quotes_key(line, key) for line in accept_lines):
            accepted.append(f'accepted: {key}')
        else:
            kept.append(finding)
    return kept, accepted


def _finding_key(finding: StructuralFinding) -> str:
    key = f'{finding.check.value} {finding.subject}'
    return f'{key} [{finding.part}]' if finding.part else key


def _quotes_key(line: str, key: str) -> bool:
    start = line.find(key)
    while start != -1:
        end = start + len(key)
        if end == len(line) or line[end].isspace():
            return True
        start = line.find(key, start + 1)
    return False


def _unique(findings: Iterable[StructuralFinding]) -> list[StructuralFinding]:
    unique: dict[str, StructuralFinding] = {}
    for finding in findings:
        unique.setdefault(_finding_key(finding), finding)
    return list(unique.values())


def _reported(findings: Iterable[StructuralFinding], finalized: bool = False) -> list[StructuralFinding]:
    return [_owned(finding, finalized) for finding in _unique(findings)]


def _owned(finding: StructuralFinding, finalized: bool = False) -> StructuralFinding:
    """Hand a finding to the finalizer when it sits in content only the finalizer writes.

    The owner is computed from the location, never guessed: in phase.md the first segment names
    the H2, and in implementation.md any later segment can name a finalize-only section or step
    field. Once the finalizer's sections exist, Success Criteria lines belong to it too, because it
    appends criteria and completes measures there. Orchestrator-owned findings stay the
    orchestrator's, whatever their location.
    """
    if finding.owner == FindingOwner.ORCHESTRATOR or not _finalizer_writes(finding, finalized):
        return finding
    return finding.model_copy(update={'owner': FindingOwner.FINALIZER})


def _finalizer_writes(finding: StructuralFinding, finalized: bool = False) -> bool:
    first, *rest = finding.location.split(' > ')
    if first == IMPLEMENTATION_FILE:
        return any(segment.casefold() in FINALIZE_ONLY_SEGMENTS for segment in rest)
    if first in FINALIZER_SECTIONS or finding.check == StructuralCheck.SUCCESS_CRITERION_MALFORMED:
        return True
    return finalized and finding.location == SUCCESS_CRITERIA_LOCATION


def _finding(
    check: StructuralCheck,
    location: str,
    subject: str,
    detail: str,
    part: str = '',
    owner: FindingOwner = FindingOwner.ARCHITECT,
) -> StructuralFinding:
    return StructuralFinding(check=check, location=location, subject=subject, part=part, owner=owner, detail=detail)


def _normalized_number(digits: str) -> str:
    return digits.lstrip('0') or '0'


def _unfenced_lines(text: str | None) -> list[str]:
    return [line for line, fenced in _lines_with_fence_state(text) if not fenced]


def _lines_with_fence_state(text: str | None) -> Iterator[tuple[str, bool]]:
    fence = ''
    for line in (text or '').splitlines():
        marker = _FENCE.match(line)
        if fence:
            if marker and _closes_fence(line, marker.group('run'), fence):
                fence = ''
            else:
                yield line, True
        elif marker:
            fence = marker.group('run')
        else:
            yield line, False


def _cli_read_lines(text: str | None, cli_reads: Callable[[str], bool]) -> list[str]:
    """Unfenced lines, plus the fenced lines the CLI parser still reads.

    The Skeleton Index and Test List readers strip each line and never skip fences, so a fenced
    entry is materialized at sign-off. Checking only those fenced lines keeps parity with the CLI
    without flagging fenced examples it ignores.
    """
    return [line for line, fenced in _lines_with_fence_state(text) if not fenced or cli_reads(line.strip())]


def _cli_reads_seam(stripped: str) -> bool:
    bullet = BULLET_PATH.match(stripped)
    return bullet is not None and ' :: ' in bullet.group('rest')


def _cli_reads_test(stripped: str) -> bool:
    bullet = BULLET_PATH.match(stripped)
    return bullet is not None and '::' in bullet.group('inner')


def _closes_fence(line: str, run: str, fence: str) -> bool:
    return run[0] == fence[0] and len(run) >= len(fence) and line.strip() == run


def _heading(line: str) -> tuple[int, str] | None:
    level = len(line) - len(line.lstrip('#'))
    rest = line[level:]
    if not 1 <= level <= 6 or (rest and not rest[0].isspace()):
        return None
    name = rest.strip()
    without_closing = name.rstrip('#')
    if without_closing != name and (not without_closing or without_closing[-1].isspace()):
        name = without_closing.strip()
    return level, name


def _sections(phase: Phase) -> list[_Section]:
    sections = [
        _Section(' > '.join(header_path), field_name, value)
        for field_name, header_path in Phase.HEADER_FIELD_MAPPING.items()
        if header_path[0] != 'Metadata' and isinstance(value := getattr(phase, field_name, None), str) and value
    ]
    sections.extend(_Section(name, '', text) for name, text in (phase.additional_sections or {}).items())
    return sections


def _is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line))


def _is_none_marker(line: str) -> bool:
    return bool(_NONE_MARKER.match(line))


def _skeleton_index_findings(phase: Phase) -> tuple[list[StructuralFinding], int]:
    layout = _module_layout_paths(phase.module_layout)
    findings: list[StructuralFinding] = []
    valid_seams = 0
    for line in _cli_read_lines(phase.skeleton_index, _cli_reads_seam):
        line_findings, is_valid_seam = _seam_line_findings(line, layout)
        findings.extend(line_findings)
        valid_seams += int(is_valid_seam)
    return findings, valid_seams


def _seam_line_findings(line: str, layout: frozenset[str]) -> tuple[list[StructuralFinding], bool]:
    stripped = line.strip()
    bullet = BULLET_PATH.match(stripped)
    if bullet is None or ' :: ' not in bullet.group('rest'):
        detail = _malformed_seam_detail(line, stripped, has_path=bullet is not None)
        if not detail:
            return [], False
        return [_finding(StructuralCheck.SEAM_ENTRY_MALFORMED, SKELETON_INDEX_LOCATION, stripped, detail)], False
    findings: list[StructuralFinding] = []
    path = bullet.group('inner')
    if layout and not _layout_covers(layout, path):
        findings.append(
            _finding(
                StructuralCheck.SEAM_PATH_NOT_IN_MODULE_LAYOUT,
                SKELETON_INDEX_LOCATION,
                path,
                'This Skeleton Index path is not covered by Module Layout; add a Module Layout bullet for it,'
                ' or for a directory that contains it, written with a trailing /.',
            )
        )
    parses = _signature_parses(bullet.group('rest').split(' :: ', 1)[1])
    if not parses:
        findings.append(
            _finding(
                StructuralCheck.SEAM_SIGNATURE_UNPARSEABLE,
                SKELETON_INDEX_LOCATION,
                stripped,
                f'This seam signature is not in the notation {SEAM_NOTATION}, where <Owner> and <member> are'
                ' each one identifier of letters, digits and underscores; rewrite it in that notation.',
            )
        )
    return findings, parses


def _malformed_seam_detail(line: str, stripped: str, has_path: bool) -> str:
    if not _is_bullet(stripped) or _is_none_marker(stripped):
        return ''
    if stripped.startswith(('*', '+')) and _cli_reads_seam(f'-{stripped[1:]}'):
        return f'Start this bullet with -, the only marker the Skeleton Index reader accepts: - `<path>` :: {SEAM_NOTATION}.'
    if not has_path and ' :: ' in stripped:
        return f'Quote this seam path in backticks at the start of the bullet: - `<path>` :: {SEAM_NOTATION}.'
    if not _is_bullet(line):
        return ''
    if has_path:
        return (
            f"Separate this entry's path from its signature with ' :: ' (- `<path>` :: {SEAM_NOTATION}),"
            ' or indent the line under its entry if it is a note.'
        )
    return f'Rewrite this bullet as - `<path>` :: {SEAM_NOTATION}, or indent it under its entry if it is a note.'


def _signature_parses(signature: str) -> bool:
    remainder, _ = strip_tags(signature.strip())
    try:
        parse_bare_signature(remainder)
    except SkeletonIndexParseError:
        return False
    return True


def _normalized_path(path: str) -> str:
    return path.strip().removeprefix('./').rstrip('/')


def _module_layout_paths(module_layout: str | None) -> frozenset[str]:
    paths: set[str] = set()
    for line in _unfenced_lines(module_layout):
        bullet = BULLET_PATH.match(line.strip())
        if bullet and (path := _normalized_path(bullet.group('inner'))):
            paths.add(path)
    return frozenset(paths)


def _layout_covers(layout: frozenset[str], path: str) -> bool:
    seam = _normalized_path(path)
    return seam in layout or any(seam.startswith(f'{entry}/') for entry in layout)


def _test_list_findings(test_list: str | None, valid_seams: int) -> list[StructuralFinding]:
    findings: list[StructuralFinding] = []
    has_bullet = False
    for line in _cli_read_lines(test_list, _cli_reads_test):
        stripped = line.strip()
        if not _is_bullet(stripped) or _is_none_marker(stripped):
            continue
        has_bullet = True
        if _is_bullet(line) and not _is_test_entry(stripped):
            findings.append(
                _finding(
                    StructuralCheck.TEST_ENTRY_WITHOUT_BEHAVIOR,
                    TEST_LIST_LOCATION,
                    stripped,
                    _test_entry_detail(stripped),
                )
            )
    if valid_seams and not has_bullet:
        findings.append(
            _finding(
                StructuralCheck.TEST_LIST_EMPTY,
                TEST_LIST_LOCATION,
                'Test List',
                'The Test List has no entries although the Skeleton Index declares seams; add one'
                ' - `<test file path>::<observable behavior>` bullet per behavior.',
            )
        )
    return findings


def _test_entry_detail(stripped: str) -> str:
    if stripped.startswith(('*', '+')) and _is_test_entry(f'-{stripped[1:]}'):
        return (
            'Start this bullet with -, the only marker the Test List reader accepts:'
            ' - `<test file path>::<observable behavior>`.'
        )
    return (
        'This Test List bullet does not open with a backticked <path>::<behavior> span; rewrite it as'
        ' - `<test file path>::<observable behavior>`.'
    )


def _is_test_entry(stripped: str) -> bool:
    bullet = BULLET_PATH.match(stripped)
    if bullet is None:
        return False
    path, separator, behavior = bullet.group('inner').partition('::')
    return bool(separator and path.strip() and behavior.strip())


def _open_entries(text: str | None) -> list[_OpenEntry]:
    entries: list[_OpenEntry] = []
    current: _OpenEntry | None = None
    for line in _unfenced_lines(text):
        if _heading(line) is not None or _is_none_marker(line):
            current = None
        elif _is_bullet(line):
            current = _open_entry(line.strip())
            entries.append(current)
        elif current is not None and line[:1].isspace():
            current.sub_lines.append(line)
    return entries


def _open_entry(stripped: str) -> _OpenEntry:
    entry = _OD_ENTRY.match(stripped)
    if entry is None:
        return _OpenEntry(stripped, '', ('entry line',), checks_sub_lines=False)
    written, number, rest = entry.group('id'), _normalized_number(entry.group('number')), entry.group('rest')
    if _SINGLE_LINE_FORM.search(rest):
        return _OpenEntry(written, number, ('single-line form',), checks_sub_lines=False)
    before_bar, bar, title = rest.lstrip().partition('|')
    if before_bar or not bar:
        return _OpenEntry(written, number, ('entry line',), checks_sub_lines=True)
    has_title = bool(_TITLE_PREFIX.sub('', title.strip()).strip())
    return _OpenEntry(written, number, () if has_title else ('title',), checks_sub_lines=True)


def _option_parts(sub_lines: list[str]) -> list[str]:
    letters: list[str] = []
    letters_with_text: set[str] = set()
    recommended: str | None = None
    for line in sub_lines:
        plain = line.replace('**', '')
        option = _OPTION_LINE.match(plain)
        if option:
            letter = option.group('letter').upper()
            letters.append(letter)
            if option.group('text').strip():
                letters_with_text.add(letter)
        elif recommended is None and (recommendation := _RECOMMENDED_LINE.match(plain)):
            recommended = recommendation.group('text')
    letter_counts = Counter(letters)
    parts: list[str] = [f'Option {letter}' for letter in REQUIRED_OPTIONS if letter not in letters_with_text]
    parts.extend(
        f'Option {letter}' for letter in letter_counts if letter not in ALLOWED_OPTIONS or letter_counts[letter] > 1
    )
    if recommended is None or _recommended_letter(recommended) not in {*letters, *REQUIRED_OPTIONS}:
        parts.append('Recommended')
    return list(dict.fromkeys(parts))


def _recommended_letter(text: str) -> str:
    tokens = [token.strip(TOKEN_PUNCTUATION) for token in text.split()]
    tokens = [token for token in tokens if token]
    if tokens and tokens[0].lower() == 'option':
        tokens = tokens[1:]
    return tokens[0].upper() if tokens else ''


def _open_entry_findings(entry: _OpenEntry) -> list[StructuralFinding]:
    parts = [*entry.head_parts, *(_option_parts(entry.sub_lines) if entry.checks_sub_lines else [])]
    return [
        _finding(
            StructuralCheck.DECISION_ENTRY_MALFORMED,
            OPEN_DECISIONS_LOCATION,
            entry.subject,
            _decision_detail(entry.subject if entry.number else '', part),
            part,
        )
        for part in parts
    ]


def _decision_detail(written_id: str, part: str) -> str:
    if not written_id:
        return (
            'This Open Design Decisions bullet is not a decision entry; rewrite it as - OD-<NNN> | <title> with'
            ' Option A, Option B and Recommended sub-lines, or remove it.'
        )
    if part == 'entry line':
        return f'The entry line for {written_id} is not - {written_id} | <title>; rewrite it in that form.'
    if part == 'single-line form':
        return (
            f'{written_id} uses the retired single-line form; put each option and the recommendation on its own'
            f' indented sub-line under - {written_id} | <title>.'
        )
    if part == 'title':
        return f'{written_id} has an empty title; write the question after the bar: - {written_id} | <title>.'
    if part == 'Recommended':
        return (
            f'{written_id} has no Recommended line naming one of its listed options; add an indented'
            ' - Recommended: <option letter> — <why> sub-line.'
        )
    if part in ('Option A', 'Option B'):
        return f'{written_id} has no {part} line with text; add an indented - {part}: <name> — <trade-off> sub-line.'
    return (
        f'{written_id} has an extra or repeated {part} line; keep one line per option letter and at most'
        ' Options A, B and C.'
    )


def _settled_entries(text: str | None) -> list[_SettledEntry]:
    entries: list[_SettledEntry] = []
    for line in _unfenced_lines(text):
        entry = _SD_ENTRY.match(line) if _is_bullet(line) else None
        if entry is not None:
            entries.append(
                _SettledEntry(
                    line=line.strip(),
                    written_id=entry.group('id'),
                    number=_normalized_number(entry.group('number')) if entry.group('number') else '',
                    values=_settled_values(entry.group('rest')),
                )
            )
    return entries


def _settled_values(rest: str) -> dict[str, str]:
    """Split an SD line into its keyed fields.

    The first segment that starts with a not-yet-seen known key opens that key. Every other
    segment, including a repeated key, continues the previous value with its ` | ` restored, so a
    signature in `supersedes=` or a quoted SD line inside `decision=` never overwrites a key.
    """
    body = rest.strip()
    values: dict[str, str] = {}
    current = ''
    for segment in body.removeprefix('|').split(' | '):
        raw_key, separator, value = segment.strip().partition('=')
        key = raw_key.strip()
        if separator and key in SD_KEYS and key not in values:
            current = key
            values[current] = value
        elif current:
            values[current] = f'{values[current]} | {segment}'
    return values


def _settled_entry_findings(entry: _SettledEntry) -> list[StructuralFinding]:
    required = REQUIRED_SD_FIELDS.get(entry.source)
    if required is None:
        return [
            _finding(
                StructuralCheck.SETTLED_ENTRY_MALFORMED,
                SETTLED_DECISIONS_LOCATION,
                entry.subject,
                f'{_settled_label(entry)} has no known source; set source= to user, user-edit, materializer,'
                ' architect or implementation.',
                'source',
                entry.owner,
            )
        ]
    if entry.source == 'user' and _SETTLES_OD_OR_CQ.match(entry.value('supersedes')):
        required = (*required, 'rejected')
    return [
        _finding(
            StructuralCheck.SETTLED_ENTRY_MALFORMED,
            SETTLED_DECISIONS_LOCATION,
            entry.subject,
            f'{_settled_label(entry)} (source={entry.source}) has no {key}= value; add | {key}=<value> to the entry.',
            key,
            entry.owner,
        )
        for key in required
        if not entry.value(key)
    ]


def _settled_label(entry: _SettledEntry) -> str:
    return entry.written_id if entry.number else 'This unnumbered settled entry'


def _overlapping_sections(phase: Phase) -> list[str]:
    names = list(phase.additional_sections or {})
    others = RESERVED_H2_NAMES | set(names)
    return [name for name in names if any(other != name and (other in name or name in other) for other in others)]


def _overlap_finding(name: str) -> StructuralFinding:
    return _finding(
        StructuralCheck.SECTION_NAME_OVERLAP,
        name,
        name,
        'This H2 name contains, or is contained in, another H2 name, so the parser can read the wrong'
        ' section; rename it so that neither name contains the other.',
    )


def _id_index(phase: Phase, open_entries: list[_OpenEntry], settled_entries: list[_SettledEntry]) -> _IdIndex:
    definitions = [
        *(
            _Definition('OD', entry.number, entry.subject, OPEN_DECISIONS_LOCATION, FindingOwner.ARCHITECT)
            for entry in open_entries
            if entry.number
        ),
        *(
            _Definition('SD', entry.number, entry.written_id, SETTLED_DECISIONS_LOCATION, entry.owner)
            for entry in settled_entries
            if entry.number
        ),
        *_flow_definitions(phase.design_shape_additional),
        *_research_definitions(phase.research_requirements),
        *_test_definitions(phase.test_list),
        *_entry_definitions(phase.success_criteria, _CRITERION_ENTRY, 'SC', SUCCESS_CRITERIA_LOCATION),
        *_entry_definitions((phase.additional_sections or {}).get(GUARDRAILS), _GUARDRAIL_ENTRY, 'G', GUARDRAILS),
    ]
    families = (*ID_FAMILIES, *BRIEF_ID_FAMILIES)
    resolvable: dict[str, set[str]] = {family: set() for family in families}
    counted: dict[str, set[str]] = {family: set() for family in families}
    duplicates: list[StructuralFinding] = []
    for definition in definitions:
        resolvable[definition.family].add(definition.number)
        if not definition.counts_for_duplicates:
            continue
        if definition.number in counted[definition.family]:
            duplicates.append(_duplicate_finding(definition))
        counted[definition.family].add(definition.number)
    superseded = _superseded_ids(settled_entries)
    for family in SETTLED_BY_SUPERSEDES:
        resolvable[family] |= superseded[family]
    return _IdIndex(resolvable=resolvable, duplicates=duplicates, settled_ods=superseded['OD'])


def _superseded_ids(settled_entries: list[_SettledEntry]) -> dict[str, set[str]]:
    superseded: dict[str, set[str]] = {family: set() for family in SETTLED_BY_SUPERSEDES}
    tokens = (token for entry in settled_entries for token in _ID_TOKEN.finditer(entry.value('supersedes')))
    for token in tokens:
        if token.group('family') in superseded:
            superseded[token.group('family')].add(_normalized_number(token.group('number')))
    return superseded


def _flow_definitions(text: str | None) -> Iterator[_Definition]:
    """Every FLOW-led bullet resolves references; only the flow list itself can define one twice.

    The UX Contract defines flows as column-0 bullets under `##### Interaction Flows` (the whole
    section when that subsection is absent). FLOW-led bullets elsewhere, such as per-flow keyboard
    paths or breakpoint notes, restate a flow, so counting them as definitions would report a
    duplicate whose suggested renumbering corrupts the contract.
    """
    lines = _unfenced_lines(text)
    scoped = any(_is_interaction_flows_heading(_heading(line)) for line in lines)
    in_flow_list = not scoped
    for line in lines:
        heading = _heading(line)
        if heading is not None and heading[0] <= INTERACTION_FLOWS_LEVEL:
            in_flow_list = not scoped or _is_interaction_flows_heading(heading)
            continue
        flow = _FLOW_DEFINITION.match(line.replace('**', ''))
        if flow:
            yield _Definition(
                'FLOW',
                _normalized_number(flow.group('number')),
                flow.group('id'),
                UX_CONTRACT_LOCATION,
                FindingOwner.ARCHITECT,
                counts_for_duplicates=in_flow_list and _is_bullet(line),
            )


def _is_interaction_flows_heading(heading: tuple[int, str] | None) -> bool:
    return heading is not None and heading[0] == INTERACTION_FLOWS_LEVEL and heading[1].lower() == INTERACTION_FLOWS


def _research_definitions(text: str | None) -> Iterator[_Definition]:
    """RP lines define their RP; `- Read:` and nested `- Applied:` lines only name one.

    A Read line's `informs:` may hold only module paths, so its first ID token can be the RP
    in `Source:`. Its RP IDs still resolve references, but never count as a second definition.
    """
    for line in _unfenced_lines(text):
        if not _is_bullet(line.strip()):
            continue
        names_only = bool(_READ_LINE.match(line) or _APPLIED_LINE.match(line))
        tokens = list(_ID_TOKEN.finditer(line))
        for token in tokens if names_only else tokens[:1]:
            if token.group('family') == 'RP':
                yield _Definition(
                    'RP',
                    _normalized_number(token.group('number')),
                    token.group(0),
                    RESEARCH_REQUIREMENTS_LOCATION,
                    FindingOwner.ORCHESTRATOR,
                    counts_for_duplicates=not names_only,
                )


def _test_entries(test_list: str | None) -> Iterator[str]:
    for line in _cli_read_lines(test_list, _cli_reads_test):
        stripped = line.strip()
        if _is_bullet(line) and _is_test_entry(stripped):
            yield stripped


def _trailing_test_id(entry: str) -> re.Match[str] | None:
    bullet = BULLET_PATH.match(entry)
    return _TRAILING_TEST_ID.search(bullet.group('rest')) if bullet else None


def _test_definitions(test_list: str | None) -> Iterator[_Definition]:
    for entry in _test_entries(test_list):
        test_id = _trailing_test_id(entry)
        if test_id is not None:
            yield _Definition(
                'T',
                _normalized_number(test_id.group('number')),
                test_id.group('id'),
                TEST_LIST_LOCATION,
                FindingOwner.ARCHITECT,
            )


def _entry_definitions(text: str | None, entry: re.Pattern[str], family: str, location: str) -> Iterator[_Definition]:
    for line in _unfenced_lines(text):
        defined = entry.match(line.replace('**', ''))
        if defined is not None:
            yield _Definition(
                family,
                _normalized_number(defined.group('number')),
                defined.group('id'),
                location,
                FindingOwner.ARCHITECT,
            )


def _duplicate_finding(definition: _Definition) -> StructuralFinding:
    return _finding(
        StructuralCheck.DUPLICATE_ID,
        definition.location,
        definition.written,
        f'{definition.written} is defined twice; give the second definition the next unused'
        f' {definition.family} number.',
        owner=definition.owner,
    )


def _still_open_findings(open_entries: list[_OpenEntry], index: _IdIndex) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.SETTLED_DECISION_STILL_OPEN,
            OPEN_DECISIONS_LOCATION,
            entry.subject,
            f'{entry.subject} is still listed as open although a settled entry supersedes it; remove it from'
            ' Open Design Decisions.',
        )
        for entry in open_entries
        if entry.number and entry.number in index.settled_ods
    ]


def _phase_reference_lines(phase: Phase, overlapping: list[str]) -> list[tuple[str, str]]:
    return [
        (section.location, line)
        for section in _sections(phase)
        if section.field_name not in REFERENCE_EXEMPT_FIELDS and section.location not in overlapping
        for line in _unfenced_lines(section.text)
    ]


def _brief_reference_lines(phase: Phase, overlapping: list[str]) -> list[tuple[str, str]]:
    """Lines where a T, SC or G token is a reference: the brief sections, Open Design Decisions and Success Criteria.

    A whole-document scan would flag ordinary prose, such as a product name ending in -7. Settled
    entries stay exempt, as for the other ID families.
    """
    return [
        (section.location, line)
        for section in _sections(phase)
        if section.location not in overlapping
        and (section.field_name in ('open_design_decisions', 'success_criteria') or _is_brief_section(section))
        for line in _unfenced_lines(section.text)
    ]


def _is_brief_section(section: _Section) -> bool:
    return not section.field_name and section.location in Phase.BRIEF_SECTIONS


def _dangling_findings(
    references: Iterable[tuple[str, str]], index: _IdIndex, token_pattern: re.Pattern[str]
) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.DANGLING_REFERENCE,
            location,
            token.group(0),
            f'{token.group(0)} matches no {DEFINED_BY[token.group("family")]} in this phase; correct the ID or'
            ' remove the reference.',
        )
        for location, line in references
        for token in token_pattern.finditer(line)
        if _normalized_number(token.group('number')) not in index.resolvable[token.group('family')]
    ]


def _test_id_findings(test_list: str | None) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.TEST_ENTRY_WITHOUT_ID,
            TEST_LIST_LOCATION,
            entry,
            'This Test List entry has no trailing — T-<n> after its closing backtick; append one with the next'
            ' unused T number.',
        )
        for entry in _test_entries(test_list)
        if _trailing_test_id(entry) is None
    ]


def _subsection_bodies(text: str | None) -> dict[str, list[str]]:
    bodies: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line, fenced in _lines_with_fence_state(text):
        heading = None if fenced else _heading(line)
        if heading is not None and heading[0] <= 3:
            current = bodies.setdefault(heading[1].casefold(), []) if heading[0] == 3 else None
        elif current is not None and line.strip():
            current.append(line)
    return bodies


def _brief_section_findings(check: StructuralCheck, name: str, text: str | None) -> list[StructuralFinding]:
    required = REQUIRED_BRIEF_SUBSECTIONS[name]
    if not text:
        return [
            _finding(
                check,
                name,
                name,
                f'## {name} is missing; add it with its {", ".join(f"### {h3}" for h3 in required)} subsections,'
                ' writing exactly - None under an empty one.',
            )
        ]
    bodies = _subsection_bodies(text)
    return [
        _finding(check, f'{name} > {h3}', name, _brief_subsection_detail(name, h3, h3.casefold() in bodies), h3)
        for h3 in required
        if not bodies.get(h3.casefold())
    ]


def _brief_subsection_detail(name: str, h3: str, present: bool) -> str:
    if present:
        return f'### {h3} under ## {name} is empty; write its entries, or exactly - None when it has none.'
    return f'## {name} has no ### {h3} subsection; add it, holding exactly - None when it has no entries.'


def _delegation_bounds_findings(phase: Phase) -> list[StructuralFinding]:
    if not any(getattr(phase, field_name) for field_name in DESIGN_SHAPE_FIELDS):
        return []
    return _brief_section_findings(
        StructuralCheck.DELEGATION_BOUNDS_INCOMPLETE,
        DELEGATION_BOUNDS,
        (phase.additional_sections or {}).get(DELEGATION_BOUNDS),
    )


def _has_finalizer_section(phase: Phase) -> bool:
    return any((phase.additional_sections or {}).get(name) for name in FINALIZER_SECTIONS)


def _finalizer_section_findings(phase: Phase) -> list[StructuralFinding]:
    if not _has_finalizer_section(phase):
        return []
    sections = phase.additional_sections or {}
    return [
        finding
        for name in FINALIZER_SECTIONS
        for finding in _brief_section_findings(StructuralCheck.BRIEF_SECTION_INCOMPLETE, name, sections.get(name))
    ]


def _success_criteria_findings(phase: Phase) -> list[StructuralFinding]:
    if not _has_finalizer_section(phase):
        return []
    findings: list[StructuralFinding] = []
    for line in _unfenced_lines(phase.success_criteria):
        if not _is_bullet(line) or _is_none_marker(line):
            continue
        plain = line.replace('**', '')
        entry = _CRITERION_ENTRY.match(plain)
        subject = entry.group('id') if entry else line.strip()
        if entry is None:
            findings.append(_criterion_finding(subject, 'id'))
        if not _MEASURE.search(plain):
            findings.append(_criterion_finding(subject, 'measure'))
    return findings


def _criterion_finding(subject: str, part: str) -> StructuralFinding:
    detail = (
        'This Success Criteria entry does not start with SC-<n>:; prefix it with the next unused SC number,'
        ' as - SC-<n>: <outcome> — measure: <check>.'
        if part == 'id'
        else 'This Success Criteria entry has no measure: part; append — measure: <a configured command or an'
        ' observable check>.'
    )
    return _finding(StructuralCheck.SUCCESS_CRITERION_MALFORMED, SUCCESS_CRITERIA_LOCATION, subject, detail, part)


def _research_copy_findings(phase: Phase) -> list[StructuralFinding]:
    grounding = (phase.additional_sections or {}).get(GROUNDING)
    if not grounding:
        return []
    agent_facing = _keyed_paths(_research_to_read_paths(grounding))
    ledger = _keyed_paths(_ledger_read_paths(phase.research_requirements))
    location = f'{GROUNDING} > {RESEARCH_TO_READ}'
    return [
        *(
            _finding(
                StructuralCheck.RESEARCH_COPIES_DISAGREE,
                location,
                path,
                'This Research to read path has no matching - Read: line in Research Requirements; remove it, since'
                ' Research to read lists exactly the validated - Read: paths.',
            )
            for key, path in agent_facing.items()
            if key not in ledger
        ),
        *(
            _finding(
                StructuralCheck.RESEARCH_COPIES_DISAGREE,
                location,
                path,
                'This - Read: path in Research Requirements is missing from Research to read; add it there with'
                ' the decisions, seams and steps it informs.',
            )
            for key, path in ledger.items()
            if key not in agent_facing
        ),
    ]


def _keyed_paths(paths: Iterable[str]) -> dict[str, str]:
    keyed: dict[str, str] = {}
    for path in paths:
        keyed.setdefault(_normalized_path(path), path)
    return keyed


def _research_to_read_paths(grounding: str) -> Iterator[str]:
    subsection = ''
    for line in _unfenced_lines(grounding):
        heading = _heading(line)
        if heading is not None and heading[0] <= 3:
            subsection = heading[1].casefold() if heading[0] == 3 else ''
        elif subsection == RESEARCH_TO_READ.casefold() and _is_bullet(line.strip()):
            span = _BACKTICK_SPAN.search(line)
            if span and (path := span.group('inner').strip()):
                yield path


def _ledger_read_paths(research_requirements: str | None) -> Iterator[str]:
    for line in _unfenced_lines(research_requirements):
        read = _READ_LINE.match(line)
        if read and (path := _read_line_path(read.group('rest'))):
            yield path


def _read_line_path(rest: str) -> str:
    span = _BACKTICK_SPAN.search(rest)
    return span.group('inner').strip() if span else rest.split(' — ', 1)[0].strip()


def _section_citations(section: _Section) -> Iterator[CitedPath]:
    subsection = ''
    for line in _unfenced_lines(section.text):
        heading = _heading(line)
        if heading is not None and heading[0] <= 3:
            subsection = heading[1] if heading[0] == 3 else ''
        own = _own_citation(section, line, subsection)
        if own is not None:
            yield own
        yield from (
            CitedPath(path=mention, kind=CitedPathKind.BEST_PRACTICES, cited_in=section.location)
            for mention in _best_practices_mentions(line)
            if own is None or mention != own.path
        )


def _own_citation(section: _Section, line: str, subsection: str) -> CitedPath | None:
    if section.field_name == 'research_requirements' and (read := _READ_LINE.match(line)):
        path = _read_line_path(read.group('rest'))
        return CitedPath(path=path, kind=CitedPathKind.READ, cited_in=section.location) if path else None
    if section.field_name == 'implementation_plan_references' and (constraint := _CONSTRAINT_LINE.match(line)):
        span = _BACKTICK_SPAN.search(constraint.group('rest'))
        path = span.group('inner').split('§', 1)[0].strip() if span else ''
        return CitedPath(path=path, kind=CitedPathKind.CONSTRAINT, cited_in=section.location) if path else None
    if _is_brief_section(section) and section.location == GROUNDING:
        return _grounding_citation(line, subsection)
    return None


def _grounding_citation(line: str, subsection: str) -> CitedPath | None:
    name = GROUNDING_PATH_SUBSECTIONS.get(subsection.casefold())
    bullet = BULLET_PATH.match(line.strip()) if name else None
    path = bullet.group('inner').strip() if bullet else ''
    return CitedPath(path=path, kind=CitedPathKind.GROUNDING, cited_in=f'{GROUNDING} > {name}') if path else None


def _best_practices_mentions(line: str) -> list[str]:
    runs = (run for run in _MENTION_DELIMITERS.split(line) if run.startswith(BEST_PRACTICES_PREFIX))
    return [mention for run in runs if (mention := _through_last_markdown_suffix(run))]


def _through_last_markdown_suffix(run: str) -> str:
    ends = [suffix.end() for suffix in _MARKDOWN_SUFFIX.finditer(run)]
    return run[: ends[-1]] if ends and ends[-1] > len(BEST_PRACTICES_PREFIX) + len('.md') else ''


def _scan_plan(markdown: str) -> _PlanScan:
    """Read implementation.md once into the facts every check needs.

    A step owns the lines below its heading up to the next heading of level four or above. Within
    a step, a column-0 field bullet opens a field, and indented or blank lines continue it, so a
    field written over several lines keeps its commands and IDs. The lines after a malformed or
    duplicate step heading belong to no step. Deviations lines are the implementers' record, which
    no agent may edit, so an ID they cite is never a reference.
    """
    scan = _PlanScan()
    position = _PlanPosition()
    for line in _unfenced_lines(markdown):
        heading = _heading(line)
        if heading is None:
            _record_plan_line(scan, position, line)
        else:
            _enter_heading(scan, position, line, heading)
        if _finalize_section(position.h2) != DEVIATIONS:
            scan.references.append((position.location, line))
        if position.label in ID_SCANNED_FIELDS:
            scan.brief_references.append((position.location, line))
    return scan


def _record_plan_line(scan: _PlanScan, position: _PlanPosition, line: str) -> None:
    if position.h2 == CHECKLIST and _CHECKLIST_ITEM.match(line):
        scan.items.append(line.strip())
    if _finalize_section(position.h2) == EXIT_CRITERIA:
        scan.exit_lines.append(line)
    if position.step is not None:
        _record_step_line(position, position.step, line)


def _record_step_line(position: _PlanPosition, step: _Step, line: str) -> None:
    step_field = _STEP_FIELD.match(line)
    if step_field is not None:
        position.label = STEP_FIELD_BY_FOLD[step_field.group('label').casefold()]
        step.fields.append((position.label, [step_field.group('value')]))
    elif position.label and (not line.strip() or line[0].isspace()):
        step.fields[-1][1].append(line)
    else:
        position.label = ''


def _finalize_section(h2: str) -> str:
    return FINALIZE_SECTION_BY_FOLD.get(h2.casefold(), '')


def _enter_heading(scan: _PlanScan, position: _PlanPosition, line: str, heading: tuple[int, str]) -> None:
    level, name = heading
    position.label = ''
    if level >= 5:
        return
    position.step = None
    if level == 1:
        position.h2 = position.h3 = ''
    elif level == 2:
        position.h2, position.h3 = name, ''
        if name in (CHECKLIST, POLICY):
            scan.sections.add(name)
        if _finalize_section(name):
            scan.finalize_sections.add(_finalize_section(name))
    elif level == 3:
        position.h3 = name
        scan.subsections.setdefault(_finalize_section(position.h2) or position.h2, set()).add(name.casefold())
        if (position.h2, name) == (BUILD_ORDER, STEPS):
            scan.sections.add(STEPS_PART)
    elif (position.h2, position.h3) == (BUILD_ORDER, STEPS):
        position.step = _record_step(scan, line.rstrip())


def _record_step(scan: _PlanScan, line: str) -> _Step | None:
    step = _STEP_HEADING.match(line)
    numbered = _NUMBERED_STEP_HEADING.match(line)
    if numbered:
        scan.numbered_steps.add(_normalized_number(numbered.group('number')))
    if step is None or not step.group('title').strip():
        scan.has_malformed_heading = True
        scan.findings.append(
            _finding(
                StructuralCheck.IMPLEMENTATION_STEP_HEADING_MALFORMED,
                f'{IMPLEMENTATION_FILE} > {STEPS_PART}',
                line.strip(),
                'This heading under Steps is not #### Step <integer>: <title>, so frozen readers skip it; rewrite'
                ' it in that form.',
            )
        )
        return None
    number = _normalized_number(step.group('number'))
    if number in scan.steps:
        scan.findings.append(
            _finding(
                StructuralCheck.DUPLICATE_ID,
                f'{IMPLEMENTATION_FILE} > {STEPS_PART}',
                f'Step {step.group("number")}',
                f'Step {step.group("number")} is defined twice; renumber the second heading to the next unused'
                ' step number and update the Checklist to match.',
            )
        )
        return None
    scan.steps[number] = step.group('number')
    opened = _Step(written=step.group('number'), number=number)
    scan.step_blocks.append(opened)
    return opened


def _missing_plan_sections(scan: _PlanScan) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.IMPLEMENTATION_SECTION_MISSING,
            IMPLEMENTATION_FILE,
            IMPLEMENTATION_FILE,
            PLAN_SECTION_DETAILS[part],
            part,
        )
        for part in REQUIRED_PLAN_PARTS
        if part not in scan.sections
    ]


def _no_steps_findings(scan: _PlanScan) -> list[StructuralFinding]:
    if STEPS_PART not in scan.sections or scan.steps or scan.has_malformed_heading:
        return []
    return [
        _finding(
            StructuralCheck.IMPLEMENTATION_NO_STEPS,
            f'{IMPLEMENTATION_FILE} > {STEPS_PART}',
            STEPS,
            'Build Order > Steps holds no #### Step <integer>: <title> heading; add one heading per step.',
        )
    ]


def _policy_subsection_findings(scan: _PlanScan) -> list[StructuralFinding]:
    if POLICY not in scan.sections:
        return []
    present = scan.subsections.get(POLICY, set())
    return [
        _finding(
            StructuralCheck.IMPLEMENTATION_SECTION_MISSING,
            f'{IMPLEMENTATION_FILE} > {POLICY}',
            IMPLEMENTATION_FILE,
            f'## Policy has no ### {subsection} subsection; add it.',
            f'{POLICY} > {subsection}',
        )
        for subsection in POLICY_SUBSECTIONS
        if subsection.casefold() not in present
    ]


def _contiguity_findings(scan: _PlanScan) -> list[StructuralFinding]:
    numbers = scan.numbered_steps
    if not scan.steps or numbers == {str(number) for number in range(1, len(numbers) + 1)}:
        return []
    return [
        _finding(
            StructuralCheck.IMPLEMENTATION_STEPS_NOT_CONTIGUOUS,
            f'{IMPLEMENTATION_FILE} > {STEPS_PART}',
            STEPS,
            'The step numbers are not exactly 1 to N, which frozen readers require; renumber the step headings'
            ' from 1 without gaps and update every reference to them in both files.',
        )
    ]


def _step_findings(step: _Step) -> list[StructuralFinding]:
    findings = _field_order_findings(step)
    if 'Files' in step.labels and not any(path.strip() for path in _spans(step.lines('Files'))):
        findings.append(
            _finding(
                StructuralCheck.IMPLEMENTATION_STEP_FILES_MISSING,
                step.location('Files'),
                step.subject,
                f'{step.subject} names no backticked path in Files, so it cannot be dispatched by its files; write'
                ' each file as create `<path>` or modify `<path>`, separated by ;.',
                'Files',
            )
        )
    if 'Verify' in step.labels and not _verify_holds_command(step.lines('Verify')):
        findings.append(
            _finding(
                StructuralCheck.IMPLEMENTATION_COMMAND_PLACEHOLDER,
                step.location('Verify'),
                step.subject,
                f'{step.subject} has no usable Verify command (empty, not backticked, TODO, no_preference or a'
                ' placeholder); write the configured command in backticks for each language that owns its files,'
                ' or the ask user marker when none is configured.',
                'Verify',
            )
        )
    return findings


def _field_order_findings(step: _Step) -> list[StructuralFinding]:
    labels = step.labels
    target = STEP_FIELDS if any(label in FINALIZE_FIELDS for label in labels) else DRAFT_FIELDS
    order = ', '.join(target)
    missing = [label for label in target if label not in labels]
    if missing:
        return [
            _field_finding(
                step, label, f'{step.subject} has no - **{label}:** field; add it, so its fields are {order}.'
            )
            for label in missing
        ]
    expected = [*target, *([''] * len(labels))]
    draft_in_order = [label for label in labels if label in DRAFT_FIELDS] == list(DRAFT_FIELDS)
    suspects = [
        label
        for label, wanted in zip(labels, expected)
        if label != wanted and (label in FINALIZE_FIELDS or not draft_in_order)
    ]
    misplaced = suspects[0] if suspects else ''
    if not misplaced:
        return []
    return [
        _field_finding(
            step,
            misplaced,
            f'{step.subject} has its fields out of order or repeated; write them once each, as {order}.',
        )
    ]


def _field_finding(step: _Step, label: str, detail: str) -> StructuralFinding:
    return _finding(
        StructuralCheck.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, step.location(label), step.subject, detail, label
    )


def _spans(lines: Iterable[str]) -> list[str]:
    return [span.group('inner') for line in lines for span in _BACKTICK_SPAN.finditer(line)]


def _verify_holds_command(lines: list[str]) -> bool:
    if _starts_with_ask_user(' '.join(lines)):
        return True
    commands = _spans(lines)
    return bool(commands) and not any(_is_placeholder_command(command) for command in commands)


def _starts_with_ask_user(text: str) -> bool:
    return text.strip().lstrip('-*+').strip().lstrip('`').strip().lower().startswith(ASK_USER_MARKER)


def _dependency_findings(scan: _PlanScan) -> list[StructuralFinding]:
    findings: list[StructuralFinding] = []
    graph: dict[str, list[str]] = {}
    for step in scan.step_blocks:
        named = {_normalized_number(token.group('number')): token.group('number') for token in _step_tokens(step)}
        findings.extend(
            _dependency_finding(step, f'Step {written}', _invalid_dependency_detail(step, number, written))
            for number, written in named.items()
            if number == step.number or number not in scan.numbered_steps
        )
        graph[step.number] = [number for number in named if number != step.number and number in scan.steps]
    findings.extend(_cycle_finding(scan, cycle) for cycle in _dependency_cycles(graph))
    return findings


def _step_tokens(step: _Step) -> Iterator[re.Match[str]]:
    for line in step.lines('Depends on'):
        yield from _STEP_TOKEN.finditer(line)


def _invalid_dependency_detail(step: _Step, number: str, written: str) -> str:
    if number == step.number:
        return f'{step.subject} depends on itself; remove Step {written} from its Depends on.'
    return f'{step.subject} depends on Step {written}, which no step heading defines; point it at an existing step.'


def _dependency_finding(step: _Step, part: str, detail: str) -> StructuralFinding:
    return _finding(
        StructuralCheck.IMPLEMENTATION_DEPENDENCY_INVALID, step.location('Depends on'), step.subject, detail, part
    )


def _cycle_finding(scan: _PlanScan, cycle: list[str]) -> StructuralFinding:
    members = sorted(cycle, key=_number_order)
    shown = ', '.join(f'Step {scan.steps[number]}' for number in members[:6])
    more = f' and {len(members) - 6} more' if len(members) > 6 else ''
    steps_by_number = {step.number: step for step in scan.step_blocks}
    return _dependency_finding(
        steps_by_number[members[0]],
        'cycle',
        f'{shown}{more} depend on one another in a cycle, so none of them can start; remove one of these dependencies.',
    )


def _number_order(number: str) -> tuple[int, str]:
    return len(number), number


def _dependency_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Strongly connected components of more than one step, found without recursion.

    Kosaraju's two passes: a post-order walk of the graph, then a walk of the reversed graph in
    reverse post-order, where each tree is one component. Iterative, so a plan with thousands of
    chained steps cannot exhaust the stack.
    """
    reverse: dict[str, list[str]] = {node: [] for node in graph}
    for node, targets in graph.items():
        for target in targets:
            reverse[target].append(node)
    assigned: set[str] = set()
    components = [_collect(root, reverse, assigned) for root in reversed(_post_order(graph)) if root not in assigned]
    return [component for component in components if len(component) > 1]


def _post_order(graph: dict[str, list[str]]) -> list[str]:
    visited: set[str] = set()
    order: list[str] = []
    for root in graph:
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(graph[root]))]
        while stack:
            node, targets = stack[-1]
            unvisited = next((target for target in targets if target not in visited), None)
            if unvisited is None:
                stack.pop()
                order.append(node)
            else:
                visited.add(unvisited)
                stack.append((unvisited, iter(graph[unvisited])))
    return order


def _collect(root: str, graph: dict[str, list[str]], assigned: set[str]) -> list[str]:
    assigned.add(root)
    stack = [root]
    members: list[str] = []
    while stack:
        node = stack.pop()
        members.append(node)
        unassigned = [target for target in graph[node] if target not in assigned]
        assigned.update(unassigned)
        stack.extend(unassigned)
    return members


def _exit_criteria_findings(scan: _PlanScan) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.IMPLEMENTATION_COMMAND_PLACEHOLDER,
            f'{IMPLEMENTATION_FILE} > {EXIT_CRITERIA}',
            EXIT_CRITERIA,
            'An Exit criteria command is empty, TODO, no_preference or a placeholder; replace it with the configured'
            ' command, or the ask user marker when none is configured.',
            command.strip(),
        )
        for command in _spans(scan.exit_lines)
        if _is_placeholder_command(command)
    ]


def _finalize_section_findings(scan: _PlanScan) -> list[StructuralFinding]:
    if not scan.finalize_sections and not any(step.is_finalized for step in scan.step_blocks):
        return []
    findings = [
        _finding(
            StructuralCheck.IMPLEMENTATION_FINALIZE_SECTION_MISSING,
            f'{IMPLEMENTATION_FILE} > {name}',
            name,
            FINALIZE_SECTION_DETAILS[name],
        )
        for name in FINALIZE_SECTIONS
        if name not in scan.finalize_sections
    ]
    if START_HERE in scan.finalize_sections:
        present = scan.subsections.get(START_HERE, set())
        findings.extend(
            _finding(
                StructuralCheck.IMPLEMENTATION_FINALIZE_SECTION_MISSING,
                f'{IMPLEMENTATION_FILE} > {START_HERE} > {subsection}',
                START_HERE,
                f'## Start here has no ### {subsection} subsection; add it.',
                subsection,
            )
            for subsection in START_HERE_SUBSECTIONS
            if subsection.casefold() not in present
        )
    if EXIT_CRITERIA in scan.finalize_sections and not _exit_criteria_name_a_command(scan.exit_lines):
        findings.append(
            _finding(
                StructuralCheck.IMPLEMENTATION_FINALIZE_SECTION_MISSING,
                f'{IMPLEMENTATION_FILE} > {EXIT_CRITERIA}',
                EXIT_CRITERIA,
                '## Exit criteria names no backticked command; add each configured command that verifies the whole'
                ' phase, in backticks.',
                'command',
            )
        )
    return findings


def _exit_criteria_name_a_command(lines: list[str]) -> bool:
    return bool(_spans(lines)) or any(_starts_with_ask_user(line) for line in lines)


def _seam_coverage_findings(scan: _PlanScan, phase: Phase) -> list[StructuralFinding]:
    if not scan.step_blocks:
        return []
    named = {_normalized_path(path) for step in scan.step_blocks for path in _spans(step.lines('Files'))}
    return [
        _finding(
            StructuralCheck.SEAM_PATH_NOT_IN_ANY_STEP,
            f'{IMPLEMENTATION_FILE} > {STEPS_PART}',
            path,
            "This Skeleton Index path is named by no step's Files; add it as a create item to the step that fills"
            ' in its skeleton.',
        )
        for path in _seam_paths(phase.skeleton_index)
        if _normalized_path(path) not in named
    ]


def _seam_paths(skeleton_index: str | None) -> Iterator[str]:
    for line in _cli_read_lines(skeleton_index, _cli_reads_seam):
        stripped = line.strip()
        bullet = BULLET_PATH.match(stripped)
        if bullet is not None and _cli_reads_seam(stripped):
            yield bullet.group('inner')


def _test_coverage_findings(scan: _PlanScan, phase: Phase) -> list[StructuralFinding]:
    if not scan.step_blocks or not all(step.is_finalized for step in scan.step_blocks):
        return []
    turned_green = {
        _normalized_number(token.group('number'))
        for step in scan.step_blocks
        for line in step.lines('Tests to turn green')
        for token in _BRIEF_ID_TOKEN.finditer(line)
        if token.group('family') == 'T'
    }
    return [
        _finding(
            StructuralCheck.TEST_NOT_IN_ANY_STEP,
            f'{IMPLEMENTATION_FILE} > {STEPS_PART} > Tests to turn green',
            definition.written,
            f'{definition.written} is turned green by no step; add it to the Tests to turn green of the step that'
            ' makes it pass.',
        )
        for definition in _first_test_definitions(phase.test_list)
        if definition.number not in turned_green
    ]


def _first_test_definitions(test_list: str | None) -> list[_Definition]:
    first: dict[str, _Definition] = {}
    for definition in _test_definitions(test_list):
        first.setdefault(definition.number, definition)
    return list(first.values())


def _phase_step_reference_findings(scan: _PlanScan, phase: Phase) -> list[StructuralFinding]:
    if not scan.steps:
        return []
    return [
        _finding(
            StructuralCheck.DANGLING_REFERENCE,
            location,
            f'Step {token.group("number")}',
            f'Step {token.group("number")} names no step heading in implementation.md; point it at an existing step'
            ' or remove the reference.',
        )
        for location, line in _phase_step_reference_lines(phase)
        for token in _STEP_TOKEN.finditer(line)
        if _normalized_number(token.group('number')) not in scan.numbered_steps
    ]


def _phase_step_reference_lines(phase: Phase) -> list[tuple[str, str]]:
    overlapping = _overlapping_sections(phase)
    sections = phase.additional_sections or {}
    return [
        *(
            (name, line)
            for name in Phase.BRIEF_SECTIONS
            if name not in overlapping
            for line in _unfenced_lines(sections.get(name))
        ),
        *(
            (OPEN_DECISIONS_LOCATION, line)
            for line in _unfenced_lines(phase.open_design_decisions)
            if _AFFECTS_LINE.match(line.replace('**', ''))
        ),
    ]


def _file_items(lines: list[str]) -> Iterator[tuple[str, CitedPathKind]]:
    for line in lines:
        verb: CitedPathKind | None = None
        for item in _FILE_ITEM.finditer(line):
            if item.group('separator'):
                verb = None
            elif item.group('verb'):
                verb = CitedPathKind(item.group('verb').lower())
            elif verb is not None and (path := item.group('path').strip()):
                yield path, verb


def _checklist_findings(scan: _PlanScan) -> list[StructuralFinding]:
    findings: list[StructuralFinding] = []
    verified: set[str] = set()
    for item in scan.items:
        written_steps = [reference.group('number') for reference in _STEP_REFERENCE.finditer(item)]
        verified.update(_normalized_number(number) for number in written_steps)
        findings.extend(_checklist_item_findings(item, written_steps, scan))
    if CHECKLIST in scan.sections:
        findings.extend(
            _finding(
                StructuralCheck.IMPLEMENTATION_STEP_UNVERIFIED,
                f'{IMPLEMENTATION_FILE} > {CHECKLIST}',
                f'Step {written}',
                f'Step {written} is named by no Checklist item; add - [ ] <item> (Step {written}) (verify: <command>).',
            )
            for number, written in scan.steps.items()
            if number not in verified
        )
    return findings


def _checklist_item_findings(item: str, written_steps: list[str], scan: _PlanScan) -> list[StructuralFinding]:
    location = f'{IMPLEMENTATION_FILE} > {CHECKLIST}'
    findings: list[StructuralFinding] = []
    if not written_steps:
        findings.append(
            _finding(
                StructuralCheck.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED,
                location,
                item,
                'This Checklist item names no (Step <integer>); add the step it verifies.',
                'step',
            )
        )
    verify_detail = _verify_detail(item)
    if verify_detail:
        findings.append(
            _finding(StructuralCheck.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, location, item, verify_detail, 'verify')
        )
    findings.extend(
        _finding(
            StructuralCheck.DANGLING_REFERENCE,
            location,
            f'Step {written}',
            f'A Checklist item names Step {written}, which no step heading defines; point it at an existing step.',
        )
        for written in written_steps
        if scan.steps and _normalized_number(written) not in scan.numbered_steps
    )
    return findings


def _verify_detail(item: str) -> str:
    commands, is_closed = _verify_commands(item)
    if not commands or not is_closed:
        return (
            'This Checklist item has no closed (verify: <command>) group; add one for each language that owns'
            " the step's files."
        )
    if any(_is_placeholder_command(command) for command in commands):
        return (
            'This Checklist item has a verify value that is empty, TODO, no_preference or a placeholder; replace'
            ' it with the configured test command, or with the (verify: ask user — …) marker when none is'
            ' configured.'
        )
    return ''


def _verify_commands(item: str) -> tuple[list[str], bool]:
    commands: list[str] = []
    start = item.find(VERIFY_OPEN)
    while start != -1:
        body = start + len(VERIFY_OPEN)
        end = _balanced_close(item, body)
        if end == -1:
            return commands, False
        commands.append(item[body:end].strip())
        start = item.find(VERIFY_OPEN, end + 1)
    return commands, True


def _balanced_close(text: str, start: int) -> int:
    depth = 1
    for index in range(start, len(text)):
        if text[index] == '(':
            depth += 1
        elif text[index] == ')':
            depth -= 1
            if depth == 0:
                return index
    return -1


def _is_placeholder_command(command: str) -> bool:
    """The one placeholder rule for step Verify, Exit criteria and Checklist verify groups.

    Empty, TODO, no_preference and a wholly bracketed value are phase 3's rule; a value holding an
    angle-bracket token such as <command> is also a placeholder. Phase 1's ask user marker never is.
    """
    bare = command.strip().strip('`').strip()
    if bare.lower().startswith(ASK_USER_MARKER):
        return False
    return not bare or bool(_PLACEHOLDER_COMMAND.match(bare) or _PLACEHOLDER_TOKEN.search(bare))
