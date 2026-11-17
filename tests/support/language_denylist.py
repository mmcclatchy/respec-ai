"""Test-only denylist of programming-language bias, shared by every guard that checks for it.

The denylist is the authority (decisions.md, "Zero language bias"): any phase-workflow text that
presumes the target project's language or ecosystem is a hit. Phase 1's template guard and phase
3's finding-detail guard both scan with it. No production code imports this module.
"""

import re
from dataclasses import dataclass

from src.platform.standards_config import available_languages
from src.utils.language_extensions import EXTENSION_TO_LANGUAGE, FRONTEND_EXTENSIONS


LANGUAGE = 'language'
FRAMEWORK = 'framework'
TOOL = 'tool'
EXTENSION = 'extension'
SYNTAX = 'syntax'

LANGUAGE_KEYS = tuple(language for language in available_languages() if language != 'universal')

# Language keys that are common English words or single letters ("Option C:", "go back to Step 8")
# are caught through these substitutes instead of the bare word. A newly excluded key must name its
# substitutes here, or B4 fails for it.
COMMON_WORD_LANGUAGE_SUBSTITUTES: dict[str, tuple[str, ...]] = {
    'c': ('`dir/file.c`', '```c'),
    'r': ('`dir/file.r`', '```r'),
    'go': ('`dir/file.go`', '```go', 'written in golang', 'run `go test ./...`'),
    'shell': ('`dir/file.sh`',),
}

DERIVED_LANGUAGE_NAMES = tuple(
    language for language in LANGUAGE_KEYS if language not in COMMON_WORD_LANGUAGE_SUBSTITUTES
)
DERIVED_EXTENSIONS = tuple(sorted(set(EXTENSION_TO_LANGUAGE) | FRONTEND_EXTENSIONS))

WORD_ENTRIES: tuple[tuple[str, str], ...] = (
    ('golang', LANGUAGE),
    ('c++', LANGUAGE),
    ('c#', LANGUAGE),
    ('sql', LANGUAGE),
    ('graphql', LANGUAGE),
    ('react', FRAMEWORK),
    ('vue', FRAMEWORK),
    ('svelte', FRAMEWORK),
    ('angular', FRAMEWORK),
    ('next.js', FRAMEWORK),
    ('htmx', FRAMEWORK),
    ('jsx', FRAMEWORK),
    ('tsx', FRAMEWORK),
    ('django', FRAMEWORK),
    ('fastapi', FRAMEWORK),
    ('pydantic', FRAMEWORK),
    ('sqlalchemy', FRAMEWORK),
    ('laravel', FRAMEWORK),
    ('express.js', FRAMEWORK),
    ('llamaindex', FRAMEWORK),
    ('llama-index', FRAMEWORK),
    ('fastmcp', FRAMEWORK),
    ('node.js', FRAMEWORK),
    ('nodejs', FRAMEWORK),
    ('deno', FRAMEWORK),
    ('pytest', TOOL),
    ('unittest', TOOL),
    ('jest', TOOL),
    ('vitest', TOOL),
    ('mocha', TOOL),
    ('rspec', TOOL),
    ('junit', TOOL),
    ('phpunit', TOOL),
    ('npm', TOOL),
    ('npx', TOOL),
    ('yarn', TOOL),
    ('pnpm', TOOL),
    ('pip', TOOL),
    ('poetry', TOOL),
    ('uv', TOOL),
    ('cargo', TOOL),
    ('gradle', TOOL),
    ('maven', TOOL),
    ('dotnet', TOOL),
    ('go test', TOOL),
    ('mix test', TOOL),
    ('mypy', TOOL),
    ('ruff', TOOL),
    ('eslint', TOOL),
    ('tsc', TOOL),
    ('async def', SYNTAX),
    ('__init__', SYNTAX),
    ('describe/it', SYNTAX),
    ('node-id', SYNTAX),
    ('base class', SYNTAX),
    ('concrete class', SYNTAX),
)

CASE_SENSITIVE_WORD_ENTRIES = (('ClassName', SYNTAX), ('method_name', SYNTAX))

# A pytest-shaped node-id suffix is followed by the test name itself, so it matches as a prefix.
PREFIX_ENTRIES = (('::test_', SYNTAX),)

FENCE_INFO_STRINGS = ('py', 'ts', 'js', 'jsx', 'tsx', 'rb', 'rs', 'kt', 'cs', 'go', 'c', 'cpp', 'r')


@dataclass(frozen=True)
class DenylistEntry:
    term: str
    category: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class Hit:
    category: str
    term: str
    line: str


def _word_entry(term: str, category: str, flags: re.RegexFlag = re.IGNORECASE) -> DenylistEntry:
    return DenylistEntry(term, category, re.compile(rf'(?<!\w){re.escape(term)}(?!\w)', flags))


def _extension_entry(extension: str) -> DenylistEntry:
    return DenylistEntry(extension, EXTENSION, re.compile(re.escape(extension) + r'(?![\w-])'))


def _fence_entry(info: str) -> DenylistEntry:
    return DenylistEntry(f'```{info}', SYNTAX, re.compile(rf'```{re.escape(info)}\b', re.IGNORECASE))


def build_denylist() -> tuple[DenylistEntry, ...]:
    return (
        *(_word_entry(name, LANGUAGE) for name in DERIVED_LANGUAGE_NAMES),
        *(_extension_entry(extension) for extension in DERIVED_EXTENSIONS),
        *(_word_entry(term, category) for term, category in WORD_ENTRIES),
        *(_word_entry(term, category, re.NOFLAG) for term, category in CASE_SENSITIVE_WORD_ENTRIES),
        *(DenylistEntry(term, category, re.compile(re.escape(term))) for term, category in PREFIX_ENTRIES),
        *(_fence_entry(info) for info in FENCE_INFO_STRINGS),
    )


DENYLIST = build_denylist()


def scan(text: str, denylist: tuple[DenylistEntry, ...] = DENYLIST) -> list[Hit]:
    return [
        Hit(entry.category, entry.term, line.strip())
        for line in text.splitlines()
        for entry in denylist
        if entry.pattern.search(line)
    ]
