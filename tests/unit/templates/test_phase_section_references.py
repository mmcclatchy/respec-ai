"""Behavior: agents are never instructed to read a Phase section that cannot exist.

See docs/phase-refactor/findings.md F3, F4 -- coder.py and spec_alignment_reviewer.py
reference "Phase Development Environment section" and "Test Organization specifications",
neither of which is a real Phase section (src/models/phase.py HEADER_FIELD_MAPPING has no
such entries). The consequence is that an agent is told to read content that was never
written, with no error -- just silent absence.
"""

import re

from src.models.phase import Phase
from src.platform.template_helpers import (
    create_coder_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
)
from src.platform.templates.agents import (
    generate_coder_template,
    generate_spec_alignment_reviewer_template,
)
from src.platform.templates.commands.phase_command import technical_phase_template
from src.platform.tui_adapters import ClaudeCodeAdapter

# A Phase section reference is written either as `Phase <H2> [> <H3>] section(s)` or as
# `<Name> specifications`. Both shapes name a section; the extractor below resolves the
# named section(s) so the test can assert they exist. This is deliberately closed: it
# does not try to parse arbitrary prose, only these two known reference shapes.
_PHASE_SECTION_REFERENCE = re.compile(r'Phase\s+([A-Z][\w\- ]*?)(?:\s*>\s*([A-Z][\w\- ]*?))?\s+sections?\b')
_SPECIFICATIONS_REFERENCE = re.compile(r'([A-Z][\w\- ]*?)\s+specifications\b')


def _known_section_names() -> set[str]:
    names: set[str] = set()
    for header_path in Phase.HEADER_FIELD_MAPPING.values():
        names.update(header_path)
    names.update(technical_phase_template_additional_section_names())
    return names


def technical_phase_template_additional_section_names() -> set[str]:
    # additional_sections keys are domain-specific H2s not present in HEADER_FIELD_MAPPING.
    # Parsed from the built markdown (rather than hardcoded) so this set can't drift from
    # phase_command.py's technical_phase_template when Phase 2 adds sections.
    return {
        line.removeprefix('## ').strip()
        for line in technical_phase_template.splitlines()
        if line.startswith('## ')
    } - {header_path[0] for header_path in Phase.HEADER_FIELD_MAPPING.values()} - {'Metadata'}


def _referenced_section_names(template: str) -> set[str]:
    referenced: set[str] = set()
    for match in _PHASE_SECTION_REFERENCE.finditer(template):
        referenced.add(match.group(1).strip())
        if match.group(2):
            referenced.add(match.group(2).strip())
    for match in _SPECIFICATIONS_REFERENCE.finditer(template):
        referenced.add(match.group(1).strip())
    return referenced


def test_agents_never_reference_a_phase_section_that_cannot_exist() -> None:
    # Scoped to the two agents findings F3/F4 named. A one-off diagnostic run of this
    # extractor against every agent template found no further phantom Phase-section
    # references, but did find prose false positives from `_SPECIFICATIONS_REFERENCE`
    # in phase_critic.py ("component specifications", "Detailed specifications") --
    # ordinary uses of the word, not a claim to read a nonexistent section. Widening
    # this test to all agents would need `_SPECIFICATIONS_REFERENCE` tightened first
    # (e.g. requiring a `Phase`-scoped subject) to avoid flagging those; out of scope
    # for Phase 0's minimal repair.
    adapter = ClaudeCodeAdapter()
    known_sections = _known_section_names()

    templates = {
        'coder': generate_coder_template(create_coder_agent_tools(adapter)),
        'spec-alignment-reviewer': generate_spec_alignment_reviewer_template(
            create_spec_alignment_reviewer_agent_tools(adapter)
        ),
    }

    phantom_references: dict[str, set[str]] = {}
    for agent_name, template in templates.items():
        referenced = _referenced_section_names(template)
        phantom = referenced - known_sections
        if phantom:
            phantom_references[agent_name] = phantom

    assert not phantom_references, f'Agents reference nonexistent Phase sections: {phantom_references}'


def test_no_h2_section_name_can_shadow_another_and_silently_swallow_content() -> None:
    # Finding F7: `## ` headings are matched by substring
    # (`h2_header in line`), so any H2 name that is a substring of another silently
    # attributes the wrong content to a field, with no error.
    all_h2_names = {header_path[0] for header_path in Phase.HEADER_FIELD_MAPPING.values()}
    all_h2_names.update(technical_phase_template_additional_section_names())
    all_h2_names.add('Metadata')

    h2_collisions = {frozenset((a, b)) for a in all_h2_names for b in all_h2_names if a != b and (a in b or b in a)}
    assert not h2_collisions, f'H2 section names shadow each other: {h2_collisions}'


_KNOWN_H3_SHADOW_DEFECTS = frozenset({frozenset(('Functional Requirements', 'Non-Functional Requirements'))})


def test_only_the_known_h3_shadow_defect_exists_KNOWN_DEFECT_inverted_in_phase_3() -> None:
    # Finding F7: `### ` headings are also matched by substring, and the H3 scan for a
    # given H2 stops at the next H2, so two H3 names collide when they share an H2 and
    # one is a substring of the other. "Functional Requirements" is a substring of
    # "Non-Functional Requirements", and both live under "## Implementation" -- today
    # this is harmless only because Functional Requirements is written before
    # Non-Functional Requirements in build_markdown()'s fixed field order, so the
    # forward scan for each header finds its own line first. If a user hand-edits
    # phase.md at the Phase 3 human gate and reorders these two H3s, the parser
    # silently swaps which content lands in which field.
    #
    # This test pins that known defect (not just the fact that a collision is
    # *possible* -- the substring relationship never changes) rather than pretending
    # it does not exist. Phase 3's `validate_document` is expected to repair base.py's
    # substring match to an equality match; when it does, invert this assertion to
    # `assert not h3_collisions`.
    h2_by_h3: dict[str, set[str]] = {}
    for header_path in Phase.HEADER_FIELD_MAPPING.values():
        h2 = header_path[0]
        if len(header_path) > 1:
            h2_by_h3.setdefault(h2, set()).add(header_path[1])

    h3_collisions: set[frozenset[str]] = set()
    for h3_names in h2_by_h3.values():
        h3_collisions.update(
            frozenset((a, b)) for a in h3_names for b in h3_names if a != b and (a in b or b in a)
        )

    assert h3_collisions == _KNOWN_H3_SHADOW_DEFECTS, (
        f'Expected only the documented Functional/Non-Functional Requirements shadow defect, got: {h3_collisions}'
    )
