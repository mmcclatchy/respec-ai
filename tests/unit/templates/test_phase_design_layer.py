"""Behaviors pinned for docs/phase-refactor/phase-2-design-layer.md.

The design layer gives Module Layout / Skeleton Index / Collaboration And Wiring /
Test List an owner (findings F1-F4): the architect must name concrete paths there
(and only there), the critic must block speculative abstraction, and the coder and
spec-alignment reviewer must read the real sections instead of the Phase 0 interim
fallback (Architecture / Testing Strategy).
"""

from src.platform.template_helpers import (
    create_coder_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
)
from src.platform.templates.agents import (
    generate_coder_template,
    generate_phase_architect_template,
    generate_phase_critic_template,
    generate_spec_alignment_reviewer_template,
)
from src.platform.tui_adapters import ClaudeCodeAdapter
from tests.support.template_contract import template_contract


def test_architect_requires_concrete_paths_in_design_sections_but_not_objectives() -> None:
    # B5: file paths are required in the design layer and forbidden in Objectives /
    # Scope / Deliverables / Development Plan -- the prohibition must be scoped, not
    # global (finding F1 was the global version of this rule).
    adapter = ClaudeCodeAdapter()
    template = generate_phase_architect_template(create_phase_architect_agent_tools(adapter))

    assert 'Module Layout' in template
    assert 'Skeleton Index' in template
    assert 'Objectives, Scope, Deliverables, Development Plan' in template, (
        'File-naming prohibition must be explicitly scoped to these sections, not global'
    )
    assert 'REQUIRED in `### Module Layout`, `### Skeleton Index`, `### Test List`' in template


def test_architect_quality_check_no_longer_asks_for_planner_file_freedom() -> None:
    # F1: phase_architect.py:520 justified hiding file names with "Does task-planner
    # have freedom to choose file organization?" -- the design layer replaces that
    # question with one that demands a real interface decision.
    adapter = ClaudeCodeAdapter()
    template = generate_phase_architect_template(create_phase_architect_agent_tools(adapter))

    assert 'freedom to choose file organization' not in template
    assert 'Would two engineers given these skeletons write the same public API?' in template


def test_critic_blocks_abstractions_with_no_stated_axis_of_variation() -> None:
    # B6: the anti-speculative-abstraction blocker is the most important addition in
    # this phase -- without it the design layer makes output worse, because the user
    # approves whatever the architect produces from Phase 3 onward.
    adapter = ClaudeCodeAdapter()
    tools = create_phase_critic_agent_tools(adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
    template = generate_phase_critic_template(tools)

    assert 'unjustified-seam' in template_contract(template).blocker_conditions()


def test_critic_shape_blockers_stay_scoped_to_module_boundaries_and_seams() -> None:
    # Cross-cutting risk 5 / decisions.md: the anti-anchoring guard keeps the shape
    # critic from drifting into a conformance checker over internal implementation
    # details -- private helpers, algorithm choice, and local naming must never block.
    adapter = ClaudeCodeAdapter()
    tools = create_phase_critic_agent_tools(adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
    template = generate_phase_critic_template(tools)

    assert 'BINDING SCOPE' in template
    assert 'Private helpers, internal data structures, algorithm choice' in template


def test_coder_builds_modules_at_paths_named_in_skeleton_index() -> None:
    # B7: the coder must consume the real design layer instead of the Phase 0 interim
    # fallback (Architecture / Testing Strategy sections), which never held file
    # layout or interfaces (finding F2).
    template = generate_coder_template(
        create_coder_agent_tools(ClaudeCodeAdapter())
    )

    assert 'Module Layout' in template
    assert 'Skeleton Index' in template
    assert 'Collaboration And Wiring' in template
    assert 'Test List' in template


def test_spec_alignment_reviewer_grades_against_skeleton_index_not_architecture() -> None:
    # Finding F4: spec_alignment_reviewer.py graded file placement against the Phase 0
    # interim fallback (System Design > Architecture). It must grade against the real
    # design layer, and treat a different *public* seam as blocking while leaving
    # internals free.
    template = generate_spec_alignment_reviewer_template(
        create_spec_alignment_reviewer_agent_tools(ClaudeCodeAdapter())
    )

    assert 'Skeleton Index' in template
    assert 'Module Layout' in template
