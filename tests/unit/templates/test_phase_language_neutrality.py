"""Guard: phase-workflow templates carry zero programming-language bias.

See docs/phase-cooperative/phase-1-language-neutral.md, behaviors B1-B6. The denylist is the
authority (decisions.md, "Zero language bias"): any phase-workflow text that presumes the target
project's language or ecosystem is a hit. Language specifics reach the architect only at runtime.
The denylist and its scanner live in tests/support/language_denylist.py, shared with phase 3's
finding-detail guard.
"""

import re
from collections import defaultdict
from functools import cache

import pytest

from src.platform.platform_selector import PlatformType
from src.platform.standards_config import build_language_defaults
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_generator import _get_agent_specs
from src.platform.templates.phase_contract_grammar import SKELETON_INDEX_PLACEHOLDER, TEST_LIST_PLACEHOLDER
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.utils.materializers import UNMATERIALIZED_LANGUAGE_NOTE, language_authoring_notes, sentinel_table
from src.utils.skeleton_generator import parse_skeleton_index, parse_test_list
from src.utils.skeleton_types import SkeletonIndexParseError
from tests.support.language_denylist import (
    COMMON_WORD_LANGUAGE_SUBSTITUTES,
    DERIVED_EXTENSIONS,
    EXTENSION,
    FRAMEWORK,
    LANGUAGE,
    LANGUAGE_KEYS,
    SYNTAX,
    TOOL,
    Hit,
    scan,
)


MODEL_OVERRIDES = {
    'reasoning': 'test-reasoning-model',
    'orchestration': 'test-orchestration-model',
    'coding': 'test-coding-model',
    'review': 'test-review-model',
}

TUIS = ('claude-code', 'opencode', 'codex')
RENDER_TARGETS = tuple((tui, platform) for tui in TUIS for platform in PlatformType)

PHASE_COMMAND = RespecAICommand.PHASE.value
PHASE_ARCHITECT = 'respec-phase-architect'
GUARDED_AGENT_PREFIX = 'respec-phase-'
CREATE_PHASE_AGENT = 'respec-create-phase'
REQUIRED_TEMPLATES = frozenset({PHASE_COMMAND, PHASE_ARCHITECT, 'respec-phase-critic', CREATE_PHASE_AGENT})


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=MODEL_OVERRIDES)
    if tui == 'codex':
        return CodexAdapter(model_overrides=MODEL_OVERRIDES)
    return ClaudeCodeAdapter()


@cache
def render_phase_workflow(tui: str, platform: PlatformType) -> dict[str, str]:
    # The same entry points generate_templates() writes artifacts through, so tool-factory
    # signature changes never move what the guard sees.
    adapter = _adapter(tui)
    plans_dir = adapter.plans_dir()
    rendered = {
        PHASE_COMMAND: TemplateCoordinator().generate_command_template(
            RespecAICommand.PHASE, platform, plans_dir=plans_dir, tui_adapter=adapter
        )
    }
    for spec in _get_agent_specs(adapter, platform, plans_dir=plans_dir):
        if spec.name.startswith(GUARDED_AGENT_PREFIX) or spec.name == CREATE_PHASE_AGENT:
            rendered[spec.name] = f'{spec.description}\n{spec.body}'
    return rendered


def _render_label(tui: str, platform: PlatformType) -> str:
    return f'{tui}/{platform.value}'


def _format_hits(renders_by_hit: dict[str, dict[Hit, set[str]]]) -> str:
    total_renders = len(RENDER_TARGETS)
    lines = ['Language bias in phase-workflow templates (template -> term -> line -> renders):']
    for template in sorted(renders_by_hit):
        hits = renders_by_hit[template]
        lines.append(f'\n{template} ({len(hits)} distinct hits)')
        for hit in sorted(hits, key=lambda h: (h.term.lower(), h.line)):
            renders = hits[hit]
            where = f'all {total_renders} renders' if len(renders) == total_renders else ', '.join(sorted(renders))
            lines.append(f'  [{hit.category}] {hit.term!r}: {hit.line[:180]}')
            lines.append(f'      in: {where}')
    return '\n'.join(lines)


def test_no_phase_workflow_artifact_names_a_language_framework_tool_extension_or_syntax() -> None:
    renders_by_hit: dict[str, dict[Hit, set[str]]] = defaultdict(lambda: defaultdict(set))
    for tui, platform in RENDER_TARGETS:
        rendered = render_phase_workflow(tui, platform)
        assert REQUIRED_TEMPLATES <= set(rendered), f'guard scanned too little for {_render_label(tui, platform)}'
        for template, text in rendered.items():
            for hit in scan(text):
                renders_by_hit[template][hit].add(_render_label(tui, platform))

    assert not renders_by_hit, _format_hits(renders_by_hit)


CATEGORY_SAMPLES = (
    (LANGUAGE, 'written in Python'),
    (EXTENSION, '`src/app/main.rs`'),
    (FRAMEWORK, 'built with Django'),
    (TOOL, 'run `pytest -q`'),
    (SYNTAX, '`async def handler`'),
)


@pytest.mark.parametrize(('category', 'sample'), CATEGORY_SAMPLES)
def test_guard_fires_for_every_denylist_category(category: str, sample: str) -> None:
    assert category in {hit.category for hit in scan(sample)}


NEUTRAL_CORPUS = (
    'Option C: keep as designed',
    'presence-only frontend decision classes',
    'the class of decision each entry belongs to',
    'interface contracts',
    'MANDATORY DECISION PROTOCOL',
    'each module owns one responsibility',
    'avoid single-function phases',
    'the verification method for each step',
    'each component of the design shape',
    'go back to Step 8',
    'run it through the Bash tool',
    'check Docker and Neo4j status via `best-practices-rag check`',
    '`.respec-ai/plans/<plan>/phases/<phase>/phase.md`',
    '`.respec-ai/config/stack.toml`',
    'the `.json` payload and the `.yaml` workflow file',
    "the user's reactions to the sketch",
    'express the decision as an option',
    'a graph node',
    'dispatch `bp-pipeline`',
    'a NoSQL store',
    'PostgreSQL',
    'deploy to AWS Lambda behind Kubernetes on GCP or Azure, monitored by Prometheus',
    'the page renders in the browser',
    'the spring release keeps the review on rails',
    'the stack the project declares',
    'read (r) and write (w) access',
    'shell out to the CLI',
    '```json',
    '```bash',
    '```toml',
    '```text',
    '```markdown',
    'etc., e.g., i.e.',
    'https://code.claude.com/docs',
)


@pytest.mark.parametrize('line', NEUTRAL_CORPUS)
def test_guard_stays_silent_on_neutral_workflow_prose(line: str) -> None:
    assert scan(line) == []


@pytest.mark.parametrize('language', LANGUAGE_KEYS)
def test_guard_catches_every_language_respec_ai_knows(language: str) -> None:
    samples = COMMON_WORD_LANGUAGE_SUBSTITUTES.get(language, (f'written in {language}',))
    missed = [sample for sample in samples if not scan(sample)]
    assert not missed, f'{language} escapes the guard through: {missed}'


@pytest.mark.parametrize('extension', DERIVED_EXTENSIONS)
def test_guard_catches_every_file_extension_respec_ai_knows(extension: str) -> None:
    assert scan(f'`dir/file{extension}`'), f'{extension} escapes the guard'


def test_test_naming_conventions_reach_the_architect_only_from_project_config() -> None:
    conventions = {language: build_language_defaults(language)['testing']['naming'] for language in LANGUAGE_KEYS}
    channels = [
        *(
            ('rendered architect', render_phase_workflow(tui, platform)[PHASE_ARCHITECT])
            for tui, platform in RENDER_TARGETS
        ),
        ('language-guidance notes', language_authoring_notes(sorted(sentinel_table()))),
    ]
    leaked = sorted(
        {
            (channel, language, naming)
            for channel, text in channels
            for language, naming in conventions.items()
            if naming and naming in text
        }
    )
    assert not leaked, f'language_standards.json naming values reach the architect outside project config: {leaked}'


_ANGLE_PLACEHOLDER = re.compile(r'<[^<>]*>')


def _taught_bullets(placeholder: str) -> list[str]:
    return [
        _ANGLE_PLACEHOLDER.sub('X', line.strip()) for line in placeholder.splitlines() if line.strip().startswith('- `')
    ]


def test_entries_written_in_the_taught_form_parse_even_without_a_materializer() -> None:
    skeleton_bullets = _taught_bullets(SKELETON_INDEX_PLACEHOLDER)
    test_bullets = _taught_bullets(TEST_LIST_PLACEHOLDER)
    assert skeleton_bullets and test_bullets

    rejected: list[str] = []
    for bullet in skeleton_bullets:
        try:
            parsed = parse_skeleton_index(bullet)
        except SkeletonIndexParseError as error:
            rejected.append(f'{bullet!r}: {error}')
            continue
        if sum(len(entry.members) for entry in parsed) != 1:
            rejected.append(f'{bullet!r}: skipped by the parser')
    assert not rejected, f'the taught Skeleton Index form is rejected by the parser: {rejected}'

    parsed_tests = [name for entry in parse_test_list('\n'.join(test_bullets)) for name in entry.test_names]
    assert len(parsed_tests) == len(test_bullets), f'Test List bullets skipped by the parser: {test_bullets}'


IDENTIFIER_RULE = 'letters, digits and underscores'


# A prose pin, kept honest by the parser test below: the parser accepts exactly one plain
# identifier for `<Owner>` and for `<member>`, so every text that teaches the notation states it.
@pytest.mark.parametrize(
    'teaching_text',
    [SKELETON_INDEX_PLACEHOLDER, UNMATERIALIZED_LANGUAGE_NOTE],
    ids=['phase-template-grammar', 'unmaterialized-language-note'],
)
def test_the_taught_notation_states_that_owner_and_member_are_each_one_plain_identifier(teaching_text: str) -> None:
    assert IDENTIFIER_RULE in teaching_text


@pytest.mark.parametrize(
    ('written', 'rewritten_by_the_rule'),
    [('A.B.c(X) -> X', 'B.c(X) -> X'), ('A.c?(X) -> X', 'A.c_(X) -> X')],
    ids=['qualified-owner', 'punctuated-member'],
)
def test_a_name_outside_the_identifier_rule_is_rejected_naming_the_rule_and_parses_once_rewritten(
    written: str, rewritten_by_the_rule: str
) -> None:
    with pytest.raises(SkeletonIndexParseError, match=IDENTIFIER_RULE):
        parse_skeleton_index(f'- `X` :: {written}')
    assert parse_skeleton_index(f'- `X` :: {rewritten_by_the_rule}')
