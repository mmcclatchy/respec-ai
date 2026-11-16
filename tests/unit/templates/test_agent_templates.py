"""Tests for agent template generation functions."""

import re

from src.platform.models import PlatformType, RoadmapOrchestratorAgentTools
from src.platform.tui_adapters import ClaudeCodeAdapter

from src.platform.template_generator import _get_agent_specs
from src.platform.template_helpers import (
    create_analyst_critic_agent_tools,
    create_create_phase_agent_tools,
    create_coder_agent_tools,
    create_patch_planner_agent_tools,
    create_plan_analyst_agent_tools,
    create_plan_critic_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_roadmap_orchestrator_agent_tools,
)
from src.platform.templates.agents import (
    generate_analyst_critic_template,
    generate_coder_template,
    generate_create_phase_template,
    generate_patch_planner_template,
    generate_plan_analyst_template,
    generate_plan_critic_template,
    generate_phase_architect_template,
    generate_phase_critic_template,
    generate_roadmap_critic_template,
    generate_roadmap_orchestrator_template,
    generate_roadmap_template,
)

from src.utils.state_manager.base import FROZEN_DISCARD_WARNING
from tests.support.template_contract import template_contract


_adapter = ClaudeCodeAdapter()

_ROADMAP_PLATFORM_TOOLS = [
    'Read(.respec-ai/plans/*/plan.md)',
    'Glob(.respec-ai/plans/*/phases/*)',
]


def _orchestrator_tools() -> RoadmapOrchestratorAgentTools:
    return create_roadmap_orchestrator_agent_tools(_adapter, _ROADMAP_PLATFORM_TOOLS)


_BANNED_ACTION_PATTERNS = (
    re.compile(r'\bshould\b', re.IGNORECASE),
    re.compile(r'\bconsider\b', re.IGNORECASE),
    re.compile(r'\bthink about\b', re.IGNORECASE),
    re.compile(r'\btry to\b', re.IGNORECASE),
    re.compile(r'\byou will\b', re.IGNORECASE),
    re.compile(r'\byour role is\b', re.IGNORECASE),
    re.compile(r'\bmay\b', re.IGNORECASE),
    re.compile(r'\bcan\b', re.IGNORECASE),
)

_AGENT_ACTION_SECTION_TOKENS = (
    'TASKS:',
    '## WORKFLOW',
    '## MODE-AWARE REVIEW CONTRACT',
    '## PROJECT CONFIGURATION',
    '## ASSESSMENT',
    '## EXPECTED PHASE STRUCTURE',
    '## TASK CONTEXT DISCOVERY',
    '## TDD METHODOLOGY',
    '## TODO LIST STRUCTURE',
    '## CODING STANDARDS',
    '## TASK AND PHASE ADHERENCE',
    '## FEEDBACK INTEGRATION',
    '## ITERATION STRATEGY',
    '## ERROR HANDLING',
    '## OUTPUT FORMAT',
    'MANDATORY ',
)


def _extract_actionable_sections(template: str, section_tokens: tuple[str, ...]) -> str:
    actionable_lines: list[str] = []
    active = False
    in_fence = False
    fence_lang = ''

    for line in template.splitlines():
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_fence:
                in_fence = False
                fence_lang = ''
            else:
                in_fence = True
                fence_lang = stripped.removeprefix('```').strip().lower()
            continue

        if stripped.startswith('#'):
            active = any(token in stripped for token in section_tokens)
        elif any(token in stripped for token in section_tokens):
            active = True
        elif stripped.startswith('VIOLATION:'):
            active = True
        elif re.match(r'^(STEP|SUB-STEP)\b', stripped):
            active = True

        include_fence_line = in_fence and fence_lang in ('', 'text')
        if active and stripped and (not in_fence or include_fence_line):
            actionable_lines.append(stripped)

    return '\n'.join(actionable_lines)


def _assert_no_soft_action_language(template: str, section_tokens: tuple[str, ...]) -> None:
    actionable = _extract_actionable_sections(template, section_tokens)
    offenders = []
    for line in actionable.splitlines():
        if any(pattern.search(line) for pattern in _BANNED_ACTION_PATTERNS):
            offenders.append(line)
    assert not offenders, f'Found soft or ambiguous action language: {offenders}'


def test_agent_actionable_section_extraction_includes_text_fences_but_skips_markdown_examples() -> None:
    template = """TASKS:
```text
This should be flagged.
```
## OUTPUT FORMAT
```markdown
This should stay ignored.
```
"""

    actionable = _extract_actionable_sections(template, _AGENT_ACTION_SECTION_TOKENS)

    assert 'This should be flagged.' in actionable
    assert 'This should stay ignored.' not in actionable


def test_patch_planner_tools_use_full_amendment_scope_keys() -> None:
    tools = create_patch_planner_agent_tools(_adapter)

    assert 'key={AMENDMENT_SCOPE_KEY}' in tools.store_amendment_scope
    assert 'key={AMENDMENT_SCOPE_KEY}' in tools.retrieve_amendment_scope


class TestPlanRoadmapTemplate:
    def test_template_structure(self) -> None:
        tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(tools)

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: respec-roadmap' in template
        assert 'description:' in template
        assert 'model: opus' in template
        assert 'tools:' in template

        # Check MCP tools section - roadmap agent only retrieves plan, doesn't create phases
        assert 'mcp__respec-ai__get_document' in template
        # Roadmap agent no longer creates phases - that's done by parallel create-phase agents
        assert 'mcp__respec-ai__add_phase' not in template
        assert 'mcp__respec-ai__list_phases' not in template

        # Check agent identity
        assert 'You are a' in template
        assert 'roadmap' in template.lower()

        # Check input/output sections
        assert 'INPUTS:' in template
        assert 'TASKS:' in template
        assert 'OUTPUTS:' in template or 'OUTPUT FORMAT' in template

    def test_template_follows_imperative_pattern(self) -> None:
        tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(tools)

        # Should contain imperative verbs
        imperative_verbs = ['Parse', 'Break', 'Extract', 'Create', 'Establish', 'Define']
        has_imperative = any(verb in template for verb in imperative_verbs)
        assert has_imperative, 'Template should contain imperative instructions'

    def test_template_no_threshold_references(self) -> None:
        tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(tools)

        # Should not contain hardcoded loop decision thresholds
        # Note: "score" references for feedback guidance are acceptable
        threshold_terms = ['85%', '90%', 'if score >= ', 'if score < ', 'score threshold']
        for term in threshold_terms:
            assert term not in template, f'Template should not contain loop decision threshold: {term}'

    def test_template_includes_error_handling(self) -> None:
        tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(tools)

        assert 'ERROR HANDLING' in template or 'Error Handling' in template


class TestRoadmapOrchestratorTemplate:
    def test_template_declares_the_worker_agents_it_dispatches(self) -> None:
        tools = _orchestrator_tools()

        assert 'Task(respec-roadmap)' in tools.tools_yaml
        assert 'Task(respec-roadmap-critic)' in tools.tools_yaml
        assert 'Task(respec-create-phase)' in tools.tools_yaml

    def test_template_is_non_interactive_and_returns_the_gate_to_its_caller(self) -> None:
        template = generate_roadmap_orchestrator_template(_orchestrator_tools())

        assert 'MANDATORY NON-INTERACTIVE CONTRACT' in template
        assert 'status: needs_user_input' in template
        assert 'The caller owns every user decision.' in template

    def test_template_resumes_an_existing_loop_without_reinitializing(self) -> None:
        template = generate_roadmap_orchestrator_template(_orchestrator_tools())

        assert 'roadmap_loop_id' in template
        assert 'SKIP this step entirely. The loop already exists.' in template
        assert 'Re-initializing an existing loop is a hard failure, not a no-op.' in template

    def test_template_resume_entry_point_is_the_generation_pass(self) -> None:
        template = generate_roadmap_orchestrator_template(_orchestrator_tools())

        assert 'This step is the resume entry point.' in template
        assert 'a fresh generate-and-critique pass is required' in template

    def test_template_keeps_the_frozen_overview_discard_guard(self) -> None:
        template = generate_roadmap_orchestrator_template(_orchestrator_tools())

        assert FROZEN_DISCARD_WARNING in template
        assert 'retrievability is not fidelity' in template

    def test_template_keeps_phase_extraction_mandatory(self) -> None:
        template = generate_roadmap_orchestrator_template(_orchestrator_tools())

        assert 'MANDATORY: PHASE EXTRACTION IS NOT OPTIONAL' in template
        assert 'Verify actual platform storage, not agent completion messages.' in template


class TestRoadmapCriticTemplate:
    def test_template_has_a_chunked_retrieval_fallback_for_large_roadmaps(self) -> None:
        # F3: get_roadmap always concatenates every phase and there is no pagination, so
        # a realistic roadmap overflowed the critic's tool-result limit. Its Read grant is
        # scoped to references/ and it has no Bash, so it had no path to the document at
        # all and correctly refused to score. It does hold get_document - it just was
        # never told to use it per phase.
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        assert 'include_phases=false' in template
        assert 'mcp__respec-ai__list_documents' in template
        assert 'doc_type="phase"' in template
        assert 'Do NOT give up.' in template

    def test_template_structure(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: respec-roadmap-critic' in template
        assert 'description:' in template
        assert 'model: opus' in template
        assert 'tools:' in template

        # Check MCP tools - roadmap-critic uses dedicated get_roadmap (no loop_id support)
        assert 'mcp__respec-ai__get_roadmap' in template  # Dedicated roadmap retrieval
        assert 'mcp__respec-ai__store_critic_feedback' in template

    def test_template_includes_critic_feedback_format(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        # Should include CriticFeedback structure
        assert '# Critic Feedback: ROADMAP-CRITIC' in template
        assert 'Overall Score' in template
        assert 'Assessment Summary' in template
        assert 'Issues and Recommendations' in template
        assert '### Blockers' in template

    def test_template_includes_fsdd_criteria(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        # Should reference FSDD framework
        assert 'FSDD' in template or '12-point' in template

        # Should include key assessment areas
        assessment_areas = ['Phase Scoping', 'Dependency', 'Implementation Readiness']
        for area in assessment_areas:
            assert area in template or area.lower() in template.lower()

    def test_template_no_threshold_references(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        # Should not contain specific threshold values
        threshold_terms = ['85%', '90%', 'threshold configured']
        for term in threshold_terms:
            assert term not in template, f'Template should not contain threshold reference: {term}'

    def test_template_enforces_tui_plan_reference_usage_when_present(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        assert 'STEP 1.7: Detect and Validate TUI Plan References' in template
        assert '.respec-ai/plans/{PLAN_NAME}/references/*.md' in template
        assert 'CALL Read(path)' in template
        assert 'TUI Plan Usage Blockers' in template
        assert 'do NOT convert them into score penalties or caps' in template
        assert 'Sparse Phase Contract Missing - BLOCKING' in template
        assert 'Refinement Output Contract Violation - BLOCKING' in template

    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- plan_name: Plan name for roadmap retrieval' in template
        assert '- loop_id: Refinement loop identifier for feedback storage' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_template_requires_exact_storage_contract(self) -> None:
        tools = create_roadmap_critic_agent_tools(_adapter)
        template = generate_roadmap_critic_template(tools)

        assert 'The feedback markdown you store MUST match the CriticFeedback parser contract exactly.' in template
        assert '# Critic Feedback: ROADMAP-CRITIC' in template
        assert '## Assessment Summary' in template
        assert '## Analysis' in template
        assert '## Issues and Recommendations' in template
        assert '## Metadata' in template
        assert 'Do NOT call `store_reviewer_result`.' in template
        assert 'Do NOT retry with alternate storage' in template
        assert 'VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.' in template


class TestCoderGroundingTemplate:
    def test_coder_template_requires_no_edit_before_grounding(self) -> None:
        tools = create_coder_agent_tools(_adapter)
        template = generate_coder_template(tools)

        assert 'Complete codebase grounding before edits' in template
        assert 'Keep a concise Grounding Evidence list in working notes: `path:line — observed fact`' in template
        assert 'Do NOT write or edit files until source/test/config evidence has been read' in template

    def test_coder_template_forbids_phase_plan_roadmap_reference_doc_edits(self) -> None:
        tools = create_coder_agent_tools(_adapter)
        template = generate_coder_template(tools)

        assert 'DO NOT write or edit `.respec-ai` Phase, roadmap, plan, implementation.md, or' in template
        assert 'Progress is reported only through the iteration handoff report.' in template

    def test_coder_template_names_the_sentinel_per_language_not_python_only(self) -> None:
        # B10 / F9: a TypeScript skeleton stubs with its own sentinel, not Python's --
        # the coder must be told to recognize the language's own marker, not hunt for
        # `raise NotImplementedError` in a `.tsx` file.
        tools = create_coder_agent_tools(_adapter)
        template = generate_coder_template(tools)

        assert "throw new Error('Not implemented')" in template
        assert 'not-implemented sentinel' in template
        assert 'DOCUMENT_AMENDMENT_REQUIRED' in template

    def test_generated_markdown_coder_has_no_edit_access_to_planning_documents(self) -> None:
        coder_spec = next(
            spec for spec in _get_agent_specs(_adapter, PlatformType.MARKDOWN) if spec.name == 'respec-coder'
        )

        assert 'Edit(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}.md)' not in coder_spec.tools
        assert 'Edit(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)' not in coder_spec.tools
        assert 'Read(.respec-ai/plans/*/phases/*/implementation.md)' in coder_spec.tools


class TestCreatePhaseTemplate:
    def test_template_structure(self) -> None:
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        template = generate_create_phase_template(tools)

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: respec-create-phase' in template
        assert 'description:' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template

    def test_template_includes_mcp_tools(self) -> None:
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        template = generate_create_phase_template(tools)

        # Should include MCP tools for single-phase retrieval/storage (not full-roadmap retrieval)
        mcp_tools = ['get_document', 'store_document']
        has_mcp_tool = any(tool in template for tool in mcp_tools)
        assert has_mcp_tool, 'Template should include MCP tools for phase operations'
        assert 'doc_type="phase"' in template, 'create-phase must retrieve the single phase, not the full roadmap'

    def test_template_supports_parallel_execution(self) -> None:
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        template = generate_create_phase_template(tools)

        # Should mention individual phase creation (not multiple)
        assert 'plan_name' in template
        assert 'Phase Name' in template
        assert 'phase_name' in template

    def test_template_includes_initialphase_creation(self) -> None:
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        template = generate_create_phase_template(tools)

        # Should reference Phase
        assert 'Phase' in template

    def test_template_uses_invocation_contract_style(self) -> None:
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        template = generate_create_phase_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- plan_name: Plan name for phase retrieval' in template
        assert '- phase_name: Phase name to retrieve' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_create_phase_validates_the_phase_before_it_stores_anything(self) -> None:
        # B30: the completeness gate must stop an incomplete phase before the MCP store, not
        # after it has already been written.
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        tasks = generate_create_phase_template(tools).split('TASKS:', 1)[1]

        first_exit = tasks.index('EXIT:')
        first_store = tasks.index(tools.store_document)

        assert first_exit < first_store

    def test_create_phase_still_reports_a_frozen_overview_discard_to_both_roadmap_paths(self) -> None:
        # B30: roadmap_command.py and roadmap_orchestrator.py dispatch this agent and scan its
        # output for this exact warning, so the trim must keep it.
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        template = generate_create_phase_template(
            create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)
        )

        assert FROZEN_DISCARD_WARNING in template
        assert 'MANDATORY CREATE PHASE OUTPUT PROTOCOL' in template


def _critic_template() -> str:
    return generate_phase_critic_template(create_phase_critic_agent_tools(_adapter))


def _architect_template() -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))


def _stored_feedback_field(template: str, field: str) -> list[str]:
    return [line.strip() for line in template.splitlines() if line.strip().startswith(f'- **{field}**:')]


# README "Critic findings": these are trade-offs a reasonable designer could settle otherwise.
_CRITIC_JUDGMENT_CALLS = frozenset(
    {
        'unjustified-seam',
        'under-surfaced-decision',
        'non-divergent-decision-options',
        'plan-constraint-violation',
        'implementation-plan-reference-not-applied',
    }
)


class TestPhaseCriticTemplate:
    def test_template_treats_best_practices_paths_as_blocking_verification(self) -> None:
        template = _critic_template()
        assert 'best-practices-rag query-kb' not in template
        assert '--force-refresh' not in template
        assert '.best-practices/*.md' in template
        assert '[Research Path Invalid - BLOCKING]: Path `{path}` does not exist' in template
        assert {'research-path-invalid', 'best-practices-reference-invalid'} <= template_contract(
            template
        ).mechanical_findings()

    def test_template_grants_read_only_review_tools(self) -> None:
        # F14: on Claude Code the tool list is what keeps the critic read-only.
        tools = create_phase_critic_agent_tools(_adapter)
        assert 'Bash' in tools.tools_yaml
        assert 'Glob' in tools.tools_yaml
        assert 'Read' in tools.tools_yaml
        assert 'update_document' not in tools.tools_yaml
        assert 'store_document' not in tools.tools_yaml
        assert 'Write' not in tools.tools_yaml
        assert 'Edit' not in tools.tools_yaml

    def test_template_declares_exactly_the_inputs_the_orchestrator_passes(self) -> None:
        # README "Agents and modes": mode, IDs and config context; the critic also gets the
        # round it stores under. Guidance arrives as the round-0 briefing feedback entry the
        # orchestrator stores ([round 0 | briefing] is the tag it writes), never as an input.
        template = _critic_template()

        assert template_contract(template).declared_inputs('### Scalar Inputs') == {
            'phase_mode',
            'loop_id',
            'plan_name',
            'phase_name',
            'review_round',
        }
        assert template_contract(template).declared_inputs('### Grouped Markdown Inputs') == {
            'project_config_context_markdown'
        }
        assert '[round 0 | briefing]' in template
        assert 'Read every project-local path listed under `### Guidance Document Paths`' in template

    def test_template_requires_exact_storage_contract(self) -> None:
        template = _critic_template()

        assert 'The feedback markdown you store MUST match the CriticFeedback parser contract exactly.' in template
        assert '# Critic Feedback: PHASE-CRITIC' in template
        assert '## Assessment Summary' in template
        assert '## Analysis' in template
        assert '## Issues and Recommendations' in template
        assert '## Metadata' in template
        assert 'Do NOT call `store_reviewer_result`.' in template
        assert 'Do NOT retry with alternate storage' in template
        assert 'VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.' in template

    def test_critic_stores_each_review_under_the_round_the_orchestrator_passes(self) -> None:
        # B4 (F9): with get_loop_status().iteration + 1 every run reported the same number and
        # replaced the last. The stored Iteration must come from review_round.
        template = _critic_template()
        tools = create_phase_critic_agent_tools(_adapter)

        iteration_fields = _stored_feedback_field(template, 'Iteration')
        assert iteration_fields
        assert all('review_round' in field for field in iteration_fields)
        assert 'get_loop_status' not in template
        assert 'get_loop_status' not in tools.tools_yaml

    def test_critic_scores_on_blockers_alone(self) -> None:
        # B4 (F7, F9): Overall Score is 100 when `### Blockers` is empty and 0 otherwise.
        template = _critic_template()

        score_fields = _stored_feedback_field(template, 'Overall Score')
        assert score_fields
        for field in score_fields:
            assert re.search(r'(?<!\d)100(?!\d)', field) and re.search(r'(?<!\d)0(?!\d)', field)
            assert 'Blockers' in field
        assert not re.search(r'\b\d+\s+points?\b|\(X/\d+|\bpenalt', template, re.IGNORECASE)
        assert 'SOFT_CAP' not in template

    def test_no_critic_finding_concerns_research_coverage_or_declined_research(self) -> None:
        # B17 (F8): a user who declines every proposal must still be able to pass review.
        contract = template_contract(_critic_template())
        findings = contract.blocker_conditions() | contract.judgment_findings()

        assert findings
        assert not {
            finding
            for finding in findings
            if 'api-research' in finding
            or 'coverage' in finding
            or 'declined' in finding
            or 'design-research' in finding
        }

    def test_the_critic_never_proposes_research(self) -> None:
        # B17: research is the architect's proposal and the user's decision, never a critic concern.
        from_report = template_contract(_critic_template()).report_section('## Research proposals')

        assert from_report == ['- None']

    def test_critic_judgment_calls_never_block_the_loop(self) -> None:
        # B19: a judgment call becomes a CQ question for the user; a blocker would loop the
        # architect on a trade-off only the user can settle.
        contract = template_contract(_critic_template())

        assert not _CRITIC_JUDGMENT_CALLS & contract.blocker_conditions()
        assert _CRITIC_JUDGMENT_CALLS <= contract.judgment_findings()

    def test_every_blocker_the_critic_raises_is_a_mechanical_finding(self) -> None:
        # README "Critic findings": `### Blockers` holds `[mechanical]` findings only, so loop
        # completion means "no open mechanical findings".
        contract = template_contract(_critic_template())

        assert contract.blocker_conditions()
        assert contract.blocker_conditions() == contract.mechanical_findings()

    def test_critic_judgment_calls_reach_the_user_as_cq_decisions(self) -> None:
        # B19: the canonical decision entry the orchestrator asks from `## Decisions needed`.
        decisions = template_contract(_critic_template()).report_section('## Decisions needed')

        assert decisions and re.match(r'^- CQ-\S+ \| ', decisions[0])
        assert [line.split(':', 1)[0] for line in decisions[1:]] == [
            '- Option A',
            '- Option B',
            '- Recommended',
            '- Affects',
        ]

    def test_critic_raises_implementation_plan_defects_as_mechanical_findings(self) -> None:
        # F5, F33: implementation.md is reviewed with the design; respec-code reads it raw from
        # this path and fails closed without it.
        template = _critic_template()

        assert '.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md' in template
        assert {
            'implementation-plan-missing',
            'step-names-no-files',
            'step-without-verify-command',
            'checklist-item-malformed',
            'verify-command-not-configured',
            'test-list-entry-not-covered',
        } <= template_contract(template).mechanical_findings()

    def test_under_surfaced_and_non_divergent_decisions_are_judgment_calls_in_review(self) -> None:
        # B19 re-anchor: these were shape-mode blockers; in review mode they are CQ questions.
        template = _critic_template()
        contract = template_contract(template)

        assert '- phase_mode:' in template
        assert {'under-surfaced-decision', 'non-divergent-decision-options'} <= contract.judgment_findings()
        assert not {'under-surfaced-decision', 'non-divergent-decision-options'} & contract.blocker_conditions()

    def test_malformed_decision_entry_is_a_mechanical_blocker_in_review(self) -> None:
        # A missing Recommended line would let "accept the recommended default" record an empty
        # decision. Phase 3 moves this check into validate_document.
        template = _critic_template()

        assert 'Malformed Decision Entry - BLOCKING' in template
        assert 'malformed-decision-entry' in template_contract(template).mechanical_findings()


class TestPlanCriticTemplate:
    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_plan_critic_agent_tools(_adapter)
        template = generate_plan_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- plan_name: Plan name for MCP plan retrieval' in template
        assert '### Grouped Markdown Inputs' in template
        assert 'previous_feedback_markdown' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template
        assert 'Progress Against Previous Feedback' in template

    def test_template_checks_source_fidelity_against_the_conversation_record(self) -> None:
        tools = create_plan_critic_agent_tools(_adapter)
        template = generate_plan_critic_template(tools)

        assert '### Step 1.5: Source Fidelity Check' in template
        assert 'Missing Conversation Record Pointer - BLOCKING' in template
        assert 'Dropped Recorded Decision - BLOCKING' in template
        assert 'Fidelity to the conversation record is NOT over-specification.' in template
        assert 'Read(.respec-ai/plans/*/references/*.md)' in template

    def test_conversation_record_marker_stays_out_of_downstream_templates(self) -> None:
        roadmap = generate_roadmap_template(create_roadmap_agent_tools(_adapter))
        roadmap_critic = generate_roadmap_critic_template(create_roadmap_critic_agent_tools(_adapter))

        assert 'Conversation Record' not in roadmap
        assert 'Conversation Record' not in roadmap_critic


class TestAgentImperativeLanguageAudit:
    def test_non_review_agent_templates_use_imperative_language_in_actionable_sections(self) -> None:
        templates = [
            generate_roadmap_template(create_roadmap_agent_tools(_adapter)),
            generate_roadmap_critic_template(create_roadmap_critic_agent_tools(_adapter)),
            generate_roadmap_orchestrator_template(_orchestrator_tools()),
            generate_create_phase_template(
                create_create_phase_agent_tools(
                    _adapter, ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit'], PlatformType.MARKDOWN
                )
            ),
            generate_phase_critic_template(create_phase_critic_agent_tools(_adapter)),
            generate_plan_critic_template(create_plan_critic_agent_tools(_adapter)),
            generate_plan_analyst_template(create_plan_analyst_agent_tools(_adapter)),
            generate_analyst_critic_template(create_analyst_critic_agent_tools(_adapter)),
            generate_phase_architect_template(create_phase_architect_agent_tools(_adapter)),
            generate_patch_planner_template(create_patch_planner_agent_tools(_adapter)),
        ]

        for template in templates:
            _assert_no_soft_action_language(template, _AGENT_ACTION_SECTION_TOKENS)


class TestAnalystCriticTemplate:
    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_analyst_critic_agent_tools(_adapter)
        template = generate_analyst_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- loop_id: Loop ID provided by Main Agent for MCP data retrieval' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template
        assert 'prior_feedback = ' in template
        assert 'Store your feedback via' in template
        assert 'store_critic_feedback' in template

    def test_template_requires_exact_storage_contract(self) -> None:
        tools = create_analyst_critic_agent_tools(_adapter)
        template = generate_analyst_critic_template(tools)

        assert 'The feedback markdown you store MUST match the CriticFeedback parser contract exactly.' in template
        assert '# Critic Feedback: ANALYST-CRITIC' in template
        assert '## Assessment Summary' in template
        assert '## Analysis' in template
        assert '## Issues and Recommendations' in template
        assert '## Metadata' in template
        assert 'Do NOT call `store_reviewer_result`.' in template
        assert 'Do NOT retry with alternate storage' in template
        assert 'VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.' in template


class TestTemplateConsistency:
    def test_template_models(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        critic_tools = create_roadmap_critic_agent_tools(_adapter)
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        create_phase_tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)

        # Roadmap uses opus (creative synthesis — architectural decomposition)
        assert 'model: opus' in generate_roadmap_template(roadmap_tools)

        # Roadmap critic stays on opus alongside roadmap; create-phase stays on sonnet.
        assert 'model: opus' in generate_roadmap_critic_template(critic_tools)
        assert 'model: sonnet' in generate_create_phase_template(create_phase_tools)

    def test_all_templates_have_required_sections(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        critic_tools = create_roadmap_critic_agent_tools(_adapter)
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        create_phase_tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)

        templates = [
            generate_roadmap_template(roadmap_tools),
            generate_roadmap_critic_template(critic_tools),
            generate_create_phase_template(create_phase_tools),
        ]

        for template in templates:
            assert 'name:' in template
            assert 'description:' in template
            assert 'TASKS:' in template
            assert ('INPUTS:' in template) or ('## Invocation Contract' in template)

    def test_no_template_contains_behavioral_descriptions(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        critic_tools = create_roadmap_critic_agent_tools(_adapter)
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        create_phase_tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)

        templates = [
            generate_roadmap_template(roadmap_tools),
            generate_roadmap_critic_template(critic_tools),
            generate_create_phase_template(create_phase_tools),
        ]

        # Anti-patterns to avoid
        behavioral_patterns = [
            'You will analyze',
            'Your role is',
            'You should consider',
            'Think about',
            'Consider different approaches',
        ]

        for template in templates:
            for pattern in behavioral_patterns:
                assert pattern not in template, f'Template contains behavioral description: {pattern}'

    def test_roadmap_template_uses_only_the_canonical_plan_reference_marker(self) -> None:
        # Nothing in respec-ai has ever written "Claude Plan:" - plan_command.py emits
        # "Plan Reference:". The second marker was a read path with no producer.
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(roadmap_tools)
        assert '"Plan Reference: `<path>`"' in template
        assert 'Claude Plan' not in template

    def test_roadmap_template_allows_reference_citation_exception_for_sparse_phase(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(roadmap_tools)
        assert 'Exception: If plan references exist, add only:' in template
        assert '### Implementation Plan References' in template
        assert '(lines X-Y)' in template

    def test_roadmap_template_includes_reference_read_permission(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(roadmap_tools)
        assert 'Read(.respec-ai/plans/*/references/*.md)' in template

    def test_phase_architect_constraint_hierarchy_has_exactly_two_sources(self) -> None:
        # The third tier scanned for "→ before implementing, read" directives, a format
        # nothing in respec-ai emits, so it could never fire. It also drove a Read()
        # fan-out. coder_contracts.py loads the same constraints from the formal section
        # alone; this matches that shape.
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'Read constraints from TWO sources in priority order' in template
        assert 'SOURCE 1 —' in template
        assert 'SOURCE 2 —' in template
        assert 'SOURCE 3' not in template
        assert 'before implementing, read' not in template
        assert 'THREE sources' not in template

    def test_patch_planner_reads_constraints_only_from_the_formal_section(self) -> None:
        planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(planner_tools)

        assert '### Implementation Plan References' in template
        assert 'before implementing, read' not in template
        assert 'backward compat' not in template

    def test_phase_architect_template_uses_only_the_canonical_plan_reference_marker(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)
        assert '"Plan Reference: `<file-path>`"' in template
        assert 'Claude Plan' not in template
        assert 'Execute knowledge base query with BOTH required flags' in template
        assert 'Always pass both `--tech` and `--topics`' in template
        assert 'Never use `--topic`' in template

    def test_phase_architect_template_requires_deviation_log_for_constraint_overrides(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)
        assert 'DEVIATION LOG PROTOCOL' in template
        assert '#### TUI Plan Deviation Log' in template

    def test_phase_architect_template_requires_semantic_reference_application(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'For every referenced implementation-plan section relevant to this Phase' in template
        assert 'apply the constraint into Objectives, Scope, Architecture, Research' in template
        assert 'not applicable' in template

    def test_phase_critic_treats_an_unapplied_implementation_plan_reference_as_a_judgment_call(self) -> None:
        # B19 re-anchor: applying a reference or justifying why it does not apply is a trade-off,
        # so it reaches the user as a CQ question instead of looping the architect.
        template = _critic_template()
        contract = template_contract(template)

        assert 'Citation-only preservation is insufficient' in template
        assert 'implementation-plan-reference-not-applied' in contract.judgment_findings()
        assert 'implementation-plan-reference-not-applied' not in contract.blocker_conditions()

    def test_phase_architect_template_requires_config_derived_verify_commands(self) -> None:
        # B5: Checklist verify commands must come from the Step's language config, not
        # a hardcoded pytest invocation copied from the one worked example.
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'never a hardcoded' in template
        assert '[commands].test' in template

    def test_phase_architect_template_no_longer_declares_a_phase_level_delivery_intent_override(self) -> None:
        # Phase 5: implementation.md's Execution Intent Policy is now the single source
        # of truth for delivery intent (docs/phase-refactor/phase-5-implementation-plan.md
        # B2). PLAN_DELIVERY_INTENT_POLICY is still read (STEP 0.55) but is now consumed
        # only by phase_mode == "implementation-plan", never written into Success Criteria.
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)
        assert 'PLAN_DELIVERY_INTENT_POLICY' in template
        assert 'Delivery Intent Override' not in template

    def test_phase_architect_template_declares_exactly_the_inputs_the_orchestrator_passes(self) -> None:
        # README "Agents and modes": mode, IDs and config context only. Guidance arrives as the
        # round-0 briefing feedback entry ([round 0 | briefing] is the tag the orchestrator
        # writes), and every guidance path in it is still read.
        template = _architect_template()

        assert template_contract(template).declared_inputs('### Scalar Inputs') == {
            'phase_mode',
            'loop_id',
            'plan_name',
            'phase_name',
        }
        assert template_contract(template).declared_inputs('### Grouped Markdown Inputs') == {
            'project_config_context_markdown'
        }
        assert '[round 0 | briefing]' in template
        assert 'Read every project-local path listed under `### Guidance Document Paths`' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_phase_architect_proposes_research_as_ledger_lines_the_orchestrator_can_dispatch(self) -> None:
        # README "Research proposal entry": Step 7 computes bp-pipeline's inputs from each
        # approved line's Technologies, Topics and Query, and routes on its tier.
        template = _architect_template()

        proposal_lines = [line.strip() for line in template.splitlines() if line.strip().startswith('- RP-')]
        assert proposal_lines
        for line in proposal_lines:
            assert 'informs:' in line
            assert 'Technologies:' in line
            assert 'Topics:' in line
            assert 'Query:' in line
            assert '| tier:' in line
        assert all(tier in template for tier in ('in-kb:', 'synthesis-only', 'web-research'))
        assert '- Synthesize:' not in template

    def test_phase_architect_tiers_proposals_from_a_cache_check_that_never_misses_on_model(self) -> None:
        # F17: check-file-cache reports a miss whenever --model differs from the model that wrote
        # the file, which would label an existing document as research to pay for.
        template = _architect_template()

        assert 'best-practices-rag generate-slug' in template
        assert 'best-practices-rag check-file-cache' in template
        assert '--model' not in template

    def test_phase_architect_may_write_only_the_implementation_plan(self) -> None:
        # Open call 1 (decisions.md): the architect puts the implementation.md draft on disk
        # itself, through a Write grant scoped to that one path. It never needs loop status (F2).
        tools = create_phase_architect_agent_tools(_adapter)
        granted = [tool.strip() for tool in tools.tools_yaml.split(',')]

        assert 'Write(.respec-ai/plans/*/phases/*/implementation.md)' in granted
        assert not [tool for tool in granted if tool.startswith('Write') and '(' not in tool]
        assert 'mcp__respec-ai__store_current_analysis' in granted
        assert 'mcp__respec-ai__get_previous_analysis' in granted
        assert 'mcp__respec-ai__get_loop_status' not in granted
        assert 'mcp__respec-ai__link_loop_to_document' not in granted

    def test_patch_planner_template_requires_execution_intent_and_deferred_risks(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)
        assert '- execution_mode: User-selected mode from respec-patch command' in template
        assert '## Invocation Contract' in template
        assert '#### Execution Intent Policy' in template
        assert '#### Deferred Risk Register' in template
        assert 'patch-mode-selection' in template
        assert '{PLAN_NAME}/{PHASE_NAME}/amendment-scope/{AMENDMENT_NAME}' in template
        assert 'Derive `AMENDMENT_NAME` from the amendment title before storage' in template

    def test_patch_planner_template_requires_codebase_evidence(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)

        assert '#### Codebase Evidence' in template
        assert '`- path/to/file.ext:123 — observed fact`' in template
        assert 'Cite only files read during codebase exploration' in template
        assert 'Codebase Evidence includes `path:line` facts for source/test/config files read' in template

    def test_patch_planner_treats_request_brief_as_authoritative(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)
        assert (
            '- request_brief: Clarified and normalized patch request from respec-patch. '
            'This is the only authoritative patch-intent input for planning.'
        ) in template
        assert 'Guidance Document Paths' in template
        assert 'Read every project-local guidance document path included in request_brief' in template
        assert 'Do NOT resolve ambiguity here; ambiguity must already be resolved before planner invocation' in template
        assert '### Unclear Change Description' not in template
        assert 'raw_request' not in template

    def test_patch_planner_pauses_for_substantive_phase_amendments(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)

        assert 'Phase Document Boundary Gate' in template
        assert 'PHASE_AMENDMENT_REQUIRED' in template
        assert 'Do NOT generate an amendment scope block' in template
        assert 'Do NOT call ' in template and 'store_review_section' in template
        assert 'Run the Phase refinement workflow (`respec-phase`) before patch coding.' in template

    def test_plan_analyst_documents_only_loop_id_as_invocation_input(self) -> None:
        tools = create_plan_analyst_agent_tools(_adapter)
        template = generate_plan_analyst_template(tools)

        assert '## Invocation Contract' in template
        assert '- loop_id: Loop ID provided by Main Agent for MCP plan retrieval' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert 'Business context, requirements, success criteria, and constraints embedded' in template
        assert 'Resolve EVERY active item under `### Blockers` before any optional refinement' in template
        assert 'CALL ' in template and 'get_feedback' in template

    def test_producer_templates_use_current_feedback_schema(self) -> None:
        roadmap_template = generate_roadmap_template(create_roadmap_agent_tools(_adapter))
        phase_template = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))

        assert 'resolve EVERY active item in `### Blockers`' in roadmap_template
        assert '"Priority Improvements"' not in phase_template
