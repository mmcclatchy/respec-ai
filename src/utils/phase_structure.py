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
RESERVED_H2_NAMES = frozenset(header_path[0] for header_path in Phase.HEADER_FIELD_MAPPING.values())

# Lines the architect cannot change: the frozen Overview is preserved by storage, and SD entries
# and the Research Requirements ledger are orchestrator-written history it carries forward verbatim.
REFERENCE_EXEMPT_FIELDS = frozenset({*FROZEN_PHASES_FIELDS, 'settled_design_decisions', 'research_requirements'})

SD_KEYS = frozenset({'source', 'supersedes', 'decision', 'rationale', 'rejected', 'binding', 'section', 'reason'})
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
class _PlanScan:
    sections: set[str] = field(default_factory=set)
    steps: dict[str, str] = field(default_factory=dict)
    numbered_steps: set[str] = field(default_factory=set)
    has_malformed_heading: bool = False
    items: list[str] = field(default_factory=list)
    references: list[tuple[str, str]] = field(default_factory=list)
    findings: list[StructuralFinding] = field(default_factory=list)


def check_phase_structure(phase: Phase) -> list[StructuralFinding]:
    open_entries = _open_entries(phase.open_design_decisions)
    settled_entries = _settled_entries(phase.settled_design_decisions)
    index = _id_index(phase, open_entries, settled_entries)
    seam_findings, valid_seams = _skeleton_index_findings(phase)
    overlapping = _overlapping_sections(phase)
    return _unique(
        [
            *seam_findings,
            *_test_list_findings(phase.test_list, valid_seams),
            *(finding for entry in open_entries for finding in _open_entry_findings(entry)),
            *(finding for entry in settled_entries for finding in _settled_entry_findings(entry)),
            *(_overlap_finding(name) for name in overlapping),
            *index.duplicates,
            *_still_open_findings(open_entries, index),
            *_dangling_findings(_phase_reference_lines(phase, overlapping), index),
        ]
    )


def extract_cited_paths(phase: Phase) -> list[CitedPath]:
    unique: dict[tuple[str, CitedPathKind, str], CitedPath] = {}
    for section in _sections(phase):
        if section.field_name in CITATION_EXEMPT_FIELDS:
            continue
        for citation in _section_citations(section):
            unique.setdefault((citation.path, citation.kind, citation.cited_in), citation)
    return list(unique.values())


def check_implementation_structure(markdown: str, phase: Phase) -> list[StructuralFinding]:
    scan = _scan_plan(markdown)
    index = _id_index(
        phase, _open_entries(phase.open_design_decisions), _settled_entries(phase.settled_design_decisions)
    )
    return _unique(
        [
            *_missing_plan_sections(scan),
            *scan.findings,
            *_no_steps_findings(scan),
            *_checklist_findings(scan),
            *_dangling_findings(scan.references, index),
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
    ]
    resolvable: dict[str, set[str]] = {family: set() for family in ID_FAMILIES}
    counted: dict[str, set[str]] = {family: set() for family in ID_FAMILIES}
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


def _dangling_findings(references: Iterable[tuple[str, str]], index: _IdIndex) -> list[StructuralFinding]:
    return [
        _finding(
            StructuralCheck.DANGLING_REFERENCE,
            location,
            token.group(0),
            f'{token.group(0)} matches no {DEFINED_BY[token.group("family")]} in this phase; correct the ID or'
            ' remove the reference.',
        )
        for location, line in references
        for token in _ID_TOKEN.finditer(line)
        if _normalized_number(token.group('number')) not in index.resolvable[token.group('family')]
    ]


def _section_citations(section: _Section) -> Iterator[CitedPath]:
    for line in _unfenced_lines(section.text):
        own = _own_citation(section, line)
        if own is not None:
            yield own
        yield from (
            CitedPath(path=mention, kind=CitedPathKind.BEST_PRACTICES, cited_in=section.location)
            for mention in _best_practices_mentions(line)
            if own is None or mention != own.path
        )


def _own_citation(section: _Section, line: str) -> CitedPath | None:
    if section.field_name == 'research_requirements' and (read := _READ_LINE.match(line)):
        rest = read.group('rest')
        span = _BACKTICK_SPAN.search(rest)
        path = span.group('inner').strip() if span else rest.split(' — ', 1)[0].strip()
        return CitedPath(path=path, kind=CitedPathKind.READ, cited_in=section.location) if path else None
    if section.field_name == 'implementation_plan_references' and (constraint := _CONSTRAINT_LINE.match(line)):
        span = _BACKTICK_SPAN.search(constraint.group('rest'))
        path = span.group('inner').split('§', 1)[0].strip() if span else ''
        return CitedPath(path=path, kind=CitedPathKind.CONSTRAINT, cited_in=section.location) if path else None
    return None


def _best_practices_mentions(line: str) -> list[str]:
    runs = (run for run in _MENTION_DELIMITERS.split(line) if run.startswith(BEST_PRACTICES_PREFIX))
    return [mention for run in runs if (mention := _through_last_markdown_suffix(run))]


def _through_last_markdown_suffix(run: str) -> str:
    ends = [suffix.end() for suffix in _MARKDOWN_SUFFIX.finditer(run)]
    return run[: ends[-1]] if ends and ends[-1] > len(BEST_PRACTICES_PREFIX) + len('.md') else ''


def _scan_plan(markdown: str) -> _PlanScan:
    scan = _PlanScan()
    h2 = h3 = ''
    for line in _unfenced_lines(markdown):
        heading = _heading(line)
        if heading is not None:
            h2, h3 = _enter_heading(scan, line, heading, h2, h3)
        elif h2 == CHECKLIST and _CHECKLIST_ITEM.match(line):
            scan.items.append(line.strip())
        scan.references.append((' > '.join(name for name in (IMPLEMENTATION_FILE, h2, h3) if name), line))
    return scan


def _enter_heading(scan: _PlanScan, line: str, heading: tuple[int, str], h2: str, h3: str) -> tuple[str, str]:
    level, name = heading
    if level == 1:
        return '', ''
    if level == 2:
        if name in (CHECKLIST, POLICY):
            scan.sections.add(name)
        return name, ''
    if level == 3:
        if (h2, name) == (BUILD_ORDER, STEPS):
            scan.sections.add(STEPS_PART)
        return h2, name
    if level == 4 and (h2, h3) == (BUILD_ORDER, STEPS):
        _record_step(scan, line.rstrip())
    return h2, h3


def _record_step(scan: _PlanScan, line: str) -> None:
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
        return
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
        return
    scan.steps[number] = step.group('number')


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
    bare = command.strip().strip('`').strip()
    if bare.lower().startswith(ASK_USER_MARKER):
        return False
    return not bare or bool(_PLACEHOLDER_COMMAND.match(bare))
