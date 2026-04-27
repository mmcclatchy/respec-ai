"""Tests for agent template generation functions."""

import re

from src.platform.models import PlatformType
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
    create_task_plan_critic_agent_tools,
    create_task_planner_agent_tools,
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
    generate_roadmap_template,
    generate_task_plan_critic_template,
    generate_task_planner_template,
)


_adapter = ClaudeCodeAdapter()
_TASK_UPDATE_TOOL = 'Edit(.respec-ai/plans/*/phases/*/tasks/*.md)'

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


def test_task_planner_tools_use_full_task_document_keys() -> None:
    tools = create_task_planner_agent_tools(_adapter)

    assert 'key={PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in tools.store_task
    assert 'key={PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in tools.link_loop


def test_patch_planner_tools_use_full_task_document_keys() -> None:
    tools = create_patch_planner_agent_tools(_adapter)

    assert 'key={PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in tools.store_task
    assert 'key={PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in tools.link_loop


def test_task_planner_carries_tui_phase_constraints_into_task_artifacts() -> None:
    tools = create_task_planner_agent_tools(_adapter)
    template = generate_task_planner_template(tools)

    assert 'MANDATORY CONSTRAINT CARRY-FORWARD' in template
    assert 'For every IMPL_PLAN_CONSTRAINTS item relevant to this Task' in template
    assert 'Acceptance Criteria: observable completion requirement' in template
    assert 'Checklist: implementation work item' in template
    assert 'Testing Strategy: verification method' in template
    assert 'Do NOT silently drop relevant TUI/Phase constraints.' in template


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


class TestRoadmapCriticTemplate:
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


class TestTaskPlanCriticTemplate:
    def test_template_enforces_tui_plan_reference_validation(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'MANDATORY TUI PLAN REFERENCE VALIDATION' in template
        assert '.respec-ai/plans/{PLAN_NAME}/references/' in template
        assert '(per plan reference: ...)' in template
        assert 'TUI Plan Deviation Log' in template
        assert 'Do NOT reduce the score or cap the score because of blockers' in template

    def test_template_uses_single_workflow_guidance_contract(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'workflow_guidance_markdown:' in template
        assert 'optional_context:' not in template
        assert 'request_brief:' not in template
        assert 'Workflow Guidance Alignment' in template
        assert '## Invocation Contract' in template
        assert '## Workflow Guidance' in template

    def test_template_uses_two_lane_score_and_blocker_contract(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert '## Two-Lane Review Contract' in template
        assert 'Lane 1 — Content score (`overall_score`)' in template
        assert 'Lane 2 — Structural/procedural blockers (`### Blockers`)' in template

    def test_template_blocks_unverifiable_task_requirements(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'Implementation Verifiability Gate' in template
        assert 'objective verification path' in template
        assert 'Map each explicit Phase objective, scope item, and deliverable' in template
        assert ('Task acceptance criteria, checklist items, implementation steps, and testing strategy') in template
        assert 'Implementation Verifiability Failure - BLOCKING' in template
        assert 'Phase Mapping Gap - BLOCKING' in template
        assert ('vague verbs such as "support", "handle", "integrate", "improve", and "ensure"') in template

    def test_template_blocks_dropped_tui_phase_constraints(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'Map each relevant implementation-plan reference or TUI-derived Phase constraint' in template
        assert 'If a relevant TUI/Phase constraint is dropped or only cited without a concrete Task mapping' in template
        assert 'add a blocker' in template

    def test_template_requires_exact_critic_feedback_storage_contract(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'The feedback markdown you store MUST match the CriticFeedback parser contract exactly.' in template
        assert '# Critic Feedback: TASK-CRITIC' in template
        assert '## Assessment Summary' in template
        assert '## Analysis' in template
        assert '## Issues and Recommendations' in template
        assert '## Metadata' in template
        assert 'Do NOT call `store_reviewer_result`.' in template
        assert 'If storage fails: STOP and report the exact error. Do NOT call `store_reviewer_result`.' in template
        assert 'VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.' in template

    def test_template_validates_patch_codebase_evidence(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'MANDATORY CODEBASE EVIDENCE VALIDATION' in template
        assert '`#### Codebase Evidence`' in template
        assert '`- path/to/file.ext:123 — observed fact`' in template
        assert '**[Codebase Evidence Missing - BLOCKING]**' in template
        assert '**[Codebase Evidence Unsupported - BLOCKING]**' in template


class TestCoderGroundingTemplate:
    def test_coder_template_requires_no_edit_before_grounding(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=[_TASK_UPDATE_TOOL],
        )
        template = generate_coder_template(tools)

        assert 'Complete codebase grounding before edits' in template
        assert 'Keep a concise Grounding Evidence list in working notes: `path:line — observed fact`' in template
        assert 'Do NOT write or edit files until source/test/config evidence has been read' in template

    def test_coder_template_forbids_phase_plan_roadmap_reference_doc_edits(self) -> None:
        tools = create_coder_agent_tools(_adapter, platform_tools=[_TASK_UPDATE_TOOL])
        template = generate_coder_template(tools)

        assert 'DO NOT write or edit `.respec-ai` Phase, roadmap, plan, or reference documents.' in template
        assert 'The only `.respec-ai` document update allowed is the assigned Task status update' in template
        assert 'DOCUMENT_AMENDMENT_REQUIRED' in template
        assert 'Update task status only through the assigned Task tool' in template

    def test_generated_markdown_coder_uses_task_update_tool_not_phase_update_tool(self) -> None:
        coder_spec = next(
            spec for spec in _get_agent_specs(_adapter, PlatformType.MARKDOWN) if spec.name == 'respec-coder'
        )

        assert 'Edit(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/tasks/{TASK_NAME}.md)' in coder_spec.tools
        assert 'Edit(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}.md)' not in coder_spec.tools


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

        # Should include MCP tools
        mcp_tools = ['get_roadmap', 'add_phase', 'store_phase']
        has_mcp_tool = any(tool in template for tool in mcp_tools)
        assert has_mcp_tool, 'Template should include MCP tools for roadmap operations'

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
        assert '- plan_name: Plan name for roadmap retrieval' in template
        assert '- phase_name: Phase name from roadmap to extract' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template


class TestPhaseCriticTemplate:
    def test_template_includes_api_research_freshness_gates(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(tools)
        assert 'API_STALE_SOFT_DAYS = 30' in template
        assert 'API_STALE_HARD_DAYS = 365' in template
        assert '--force-refresh' in template
        assert 'per-service research coverage' in template
        assert '.best-practices/*.md' in template
        assert 'API Research Coverage Missing - BLOCKING' in template
        assert 'Best-Practices Reference Invalid - BLOCKING' in template
        assert 'API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT' in template

    def test_template_enforces_deterministic_api_detection_and_mode_aware_coverage(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(tools)
        assert 'API_DETECTION_TEXT = concatenate text from:' in template
        assert 'Normalize each candidate deterministically:' in template
        assert 'Exclude internal/local-only candidates:' in template
        assert (
            'Validate all "- Read:" lines found under Research Requirements regardless of subsection headers.'
            in template
        )
        assert "line.startswith('- Read:')" in template
        assert 'IF validation_mode == "post_synthesis":' in template
        assert (
            'API_MARKER_READ_CANDIDATES = VALID_BP_READ_PATHS items containing both `apidocs` and `apiintegration`'
            in template
        )
        assert 'API_DOC_MARKER_GLOB_PATHS = []' in template
        assert 'CONTENT_HAS_OFFICIAL_SOURCE' in template
        assert 'CONTENT_HAS_CLIENT_DECISION' in template
        assert 'HAS_VALID_BP_READ_COVERAGE = len(VALIDATED_API_READ_PATHS) > 0' in template
        assert 'contains both `apidocs` and `apiintegration`' in template
        assert 'filename/API-name substring matches alone' in template
        assert (
            'HAS_VALID_BP_READ_COVERAGE = any VALID_BP_READ_PATHS item contains api_name OR API_SLUG_TOKEN'
            not in template
        )
        assert 'For each api_name in APIS_WITH_VALID_BP_READ_COVERAGE:' in template
        assert 'APIS_MISSING_FINAL_DOCS = []' in template
        assert 'API Research Coverage Missing - BLOCKING' in template
        assert 'API Research Final Docs Missing - BLOCKING' in template
        assert '"detected_external_apis": EXTERNAL_APIS' in template
        assert '"apis_missing_final_docs": APIS_MISSING_FINAL_DOCS' in template

    def test_template_grants_bash_and_glob_tools(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        assert 'Bash' in tools.tools_yaml
        assert 'Glob' in tools.tools_yaml

    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- validation_mode: Optional scalar input.' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_template_uses_two_lane_score_and_blocker_contract(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(tools)

        assert '## Two-Lane Review Contract' in template
        assert 'Lane 1 — Content score (`overall_score`):' in template
        assert 'Lane 2 — Structural/procedural blockers (`### Blockers`):' in template
        assert 'Structural blockers gate readiness through `### Blockers`' in template
        assert 'do NOT change the content score' in template

    def test_template_requires_exact_storage_contract(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(tools)

        assert 'The feedback markdown you store MUST match the CriticFeedback parser contract exactly.' in template
        assert '# Critic Feedback: PHASE-CRITIC' in template
        assert '## Assessment Summary' in template
        assert '## Analysis' in template
        assert '## Issues and Recommendations' in template
        assert '## Metadata' in template
        assert 'Do NOT call `store_reviewer_result`.' in template
        assert 'Do NOT retry with alternate storage' in template
        assert 'VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.' in template


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


class TestAgentImperativeLanguageAudit:
    def test_non_review_agent_templates_use_imperative_language_in_actionable_sections(self) -> None:
        templates = [
            generate_roadmap_template(create_roadmap_agent_tools(_adapter)),
            generate_roadmap_critic_template(create_roadmap_critic_agent_tools(_adapter)),
            generate_create_phase_template(
                create_create_phase_agent_tools(
                    _adapter, ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit'], PlatformType.MARKDOWN
                )
            ),
            generate_phase_critic_template(create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)),
            generate_plan_critic_template(create_plan_critic_agent_tools(_adapter)),
            generate_plan_analyst_template(create_plan_analyst_agent_tools(_adapter)),
            generate_analyst_critic_template(create_analyst_critic_agent_tools(_adapter)),
            generate_phase_architect_template(create_phase_architect_agent_tools(_adapter)),
            generate_task_planner_template(create_task_planner_agent_tools(_adapter)),
            generate_task_plan_critic_template(create_task_plan_critic_agent_tools(_adapter)),
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

    def test_roadmap_template_accepts_legacy_and_new_plan_reference_markers(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        template = generate_roadmap_template(roadmap_tools)
        assert '"Plan Reference: `<path>`"' in template
        assert '"Claude Plan: `<path>`" (legacy)' in template

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

    def test_phase_architect_template_accepts_legacy_and_new_plan_reference_markers(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)
        assert '"Plan Reference: `<file-path>`"' in template
        assert '"Claude Plan: `<file-path>`" in STRATEGIC_PLAN_MARKDOWN (legacy)' in template
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

    def test_phase_critic_template_blocks_unapplied_implementation_plan_references(self) -> None:
        critic_tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000)
        template = generate_phase_critic_template(critic_tools)

        assert 'Verify Implementation Plan Reference Semantic Application' in template
        assert 'Citation-only preservation is insufficient' in template
        assert 'Implementation Plan Reference Not Applied - BLOCKING' in template

    def test_phase_architect_template_propagates_delivery_intent_override_contract(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)
        assert 'PLAN_DELIVERY_INTENT_POLICY' in template
        assert '#### Delivery Intent Override' in template
        assert 'Mode: inherit-plan-default' in template

    def test_phase_architect_template_uses_invocation_contract_style(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- optional_instructions: Additional user guidance for phase development (if provided)' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_phase_architect_template_requires_official_api_doc_research_markers(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'OFFICIAL API DOCUMENTATION RESEARCH PROTOCOL' in template
        assert '`apidocs` and `apiintegration`' in template
        assert 'Do NOT browse the web directly from this agent.' in template
        assert 'Do NOT use PascalCase marker variants' in template
        assert 'filename marker matches are candidate filters only' in template.lower()
        assert 'official source URLs' in template
        assert 'authentication, endpoints/operations or SDK/client method contracts' in template
        assert 'request/response schemas or payload contracts' in template
        assert 'SDK/client library vs direct HTTP based on official docs' in template
        assert 'Do not prefer SDKs globally.' in template

    def test_task_planner_template_accepts_structured_reference_inputs(self) -> None:
        task_planner_tools = create_task_planner_agent_tools(_adapter)
        template = generate_task_planner_template(task_planner_tools)
        assert 'reference_context_markdown' in template
        assert 'workflow_guidance_markdown' in template
        assert '## Reference Context' in template
        assert '### Structured References' in template
        assert 'PHASE_DEVIATION_OVERRIDES' in template
        assert 'Read(.respec-ai/plans/*/references/*.md)' in template
        assert '## IMPLEMENTATION PLAN REFERENCE INTEGRATION' in template
        assert '(per plan reference: filename.md § "Section Name" (lines X-Y))' in template
        assert '### Technology Stack Reference' in template
        assert '### Steps' in template
        assert '#### Execution Intent Policy' in template
        assert '#### Deferred Risk Register' in template
        assert 'DR-001' in template
        assert '{PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in template
        assert 'compute TASK_NAME explicitly' in template

    def test_patch_planner_template_requires_execution_intent_and_deferred_risks(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)
        assert '- execution_mode: User-selected mode from respec-patch command' in template
        assert '## Invocation Contract' in template
        assert '#### Execution Intent Policy' in template
        assert '#### Deferred Risk Register' in template
        assert 'patch-mode-selection' in template
        assert '{PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}' in template
        assert 'Derive `TASK_NAME` from the amendment task title before storage' in template

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
        assert 'Do NOT resolve ambiguity here; ambiguity must already be resolved before planner invocation' in template
        assert '### Unclear Change Description' not in template
        assert 'raw_request' not in template

    def test_patch_planner_pauses_for_substantive_phase_amendments(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)

        assert 'Phase Document Boundary Gate' in template
        assert 'PHASE_AMENDMENT_REQUIRED' in template
        assert 'Do NOT generate an amendment Task' in template
        assert 'Do NOT call ' in template and 'store_document' in template
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
        task_template = generate_task_planner_template(create_task_planner_agent_tools(_adapter))

        assert 'resolve EVERY active item in `### Blockers`' in roadmap_template
        assert '"Priority Improvements"' not in phase_template
        assert 'Resolve ALL active items' in task_template
        assert 'CriticFeedback `### Blockers`' in task_template
