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
)


_adapter = ClaudeCodeAdapter()

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


class TestPhaseArchitectShapeMode:
    def test_shape_mode_declared_and_scoped_to_design_shape_only(self) -> None:
        # Phase 3, decisions.md "critic runs after user approval": the architect must not
        # produce full implementation detail when phase_mode="shape" - that's exactly the
        # unapproved-design problem the human gate exists to stop.
        tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(tools)

        assert '- phase_mode:' in template
        assert 'phase_mode == "shape"' in template
        assert 'Do NOT write Architecture prose beyond what justifies the seams' in template

    def test_detail_mode_preserves_an_already_settled_shape_verbatim(self) -> None:
        # Once a human has approved the design at the Phase 3 gate (Shape Gate ==
        # shape-settled/shape-amended), the detail-act architect must not regenerate
        # Design Shape/Design Decisions - that would silently overwrite what the user
        # just approved.
        tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(tools)

        assert 'shape-settled' in template
        assert 'VERBATIM' in template

    def test_shape_mode_marks_consequential_internals_for_the_skeleton_opt_in_prompt(self) -> None:
        # phase_command.py Step 7 parses Skeleton Index entries marked "internal,
        # consequential" to build its multiSelect skeleton opt-in prompt. Without an
        # instruction telling the architect to emit that marker, Step 7's source list is
        # always empty and the prompt never fires.
        tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(tools)

        assert 'internal, consequential' in template


class TestPhaseCriticTemplate:
    def test_template_treats_best_practices_paths_as_blocking_verification(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)
        assert 'best-practices-rag query-kb' not in template
        assert '--force-refresh' not in template
        assert 'per-service research coverage' in template
        assert '.best-practices/*.md' in template
        assert '[Research Path Invalid - BLOCKING]: Path `{path}` does not exist' in template
        assert 'API Research Coverage Missing - BLOCKING' in template
        assert 'Best-Practices Reference Invalid - BLOCKING' in template
        assert 'API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT' not in template
        assert 'Hard stale blocking' not in template

    def test_template_enforces_deterministic_api_detection_and_mode_aware_coverage(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)
        assert 'API_DETECTION_TEXT = concatenate text from:' in template
        assert 'Normalize each candidate deterministically:' in template
        assert 'Exclude internal/local-only candidates:' in template
        assert (
            'Validate all "- Read:" lines found under Research Requirements regardless of subsection headers.'
            in template
        )
        assert "line.startswith('- Read:')" in template
        assert 'READ_BLOCKS = []' in template
        assert 'READ_BLOCK_METADATA_BY_PATH = {}' in template
        assert 'IF validation_mode == "post_synthesis":' in template
        assert 'API_POTENTIAL_MATCHES = []' in template
        assert 'rg -il --fixed-strings "{api_name}" .best-practices/ || true' in template
        assert 'cat "{potential_path}" | head -n 25' in template
        assert 'OVERVIEW_HEAD contains `## Overview`' in template
        assert 'quick-scan matches are not coverage evidence by themselves' in template
        assert 'API_DOC_CANDIDATES = VALID_BP_READ_PATHS' in template
        assert 'METADATA_MATCHES_API' in template
        assert 'METADATA_MATCHES_RUNTIME' in template
        assert 'CONTENT_MATCHES_RUNTIME' in template
        assert 'CONTENT_HAS_OFFICIAL_SOURCE' in template
        assert 'CONTENT_HAS_CLIENT_DECISION' in template
        assert (
            '(METADATA_MATCHES_API OR CONTENT_MATCHES_API) AND (METADATA_MATCHES_RUNTIME OR CONTENT_MATCHES_RUNTIME)'
        ) in template
        assert 'Generic provider docs are insufficient' in template
        assert 'HAS_VALID_BP_READ_COVERAGE = len(VALIDATED_API_READ_PATHS) > 0' in template
        assert 'API doc filenames are never authoritative' in template
        assert 'phase-cited `Read:` `.best-practices/*.md` paths' in template
        assert 'API_DOC_MARKER_GLOB_PATHS' not in template
        assert 'API_MARKER_READ_CANDIDATES' not in template
        assert '.best-practices/*apidocs*apiintegration*.md' not in template
        assert (
            'HAS_VALID_BP_READ_COVERAGE = any VALID_BP_READ_PATHS item contains api_name OR API_SLUG_TOKEN'
            not in template
        )
        assert 'APIS_MISSING_FINAL_DOCS = []' in template
        assert 'API Research Coverage Missing - BLOCKING' in template
        assert 'API Research Final Docs Missing - BLOCKING' in template
        assert '"detected_external_apis": EXTERNAL_APIS' in template
        assert '"apis_missing_final_docs": APIS_MISSING_FINAL_DOCS' in template
        assert '"api_potential_matches": API_POTENTIAL_MATCHES' in template
        assert 'POST_SYNTHESIS_LOOP_STATUS = ' in template
        assert 'POST_SYNTHESIS_ITERATION = POST_SYNTHESIS_LOOP_STATUS.iteration + 1' in template
        assert 'POST_SYNTHESIS_SCORE = POST_SYNTHESIS_LOOP_STATUS.current_score' in template
        assert 'ERROR: "Post-synthesis validation cannot preserve a non-zero phase score"' in template
        assert 'MUST NOT store feedback with iteration=0.' in template
        assert 'MUST NOT store feedback with overall_score=0.' in template
        assert 'Set `overall_score` to `POST_SYNTHESIS_SCORE`, never `0`' in template

    def test_template_grants_bash_and_glob_tools(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        assert 'Bash' in tools.tools_yaml
        assert 'Glob' in tools.tools_yaml
        assert 'Read' in tools.tools_yaml
        assert 'mcp__respec-ai__get_loop_status' in tools.tools_yaml

    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- validation_mode: Optional scalar input.' in template
        assert '### Grouped Markdown Inputs' in template
        assert 'workflow_guidance_markdown' in template
        assert '### Guidance Document Paths' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_template_uses_two_lane_score_and_blocker_contract(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert '## Two-Lane Review Contract' in template
        assert 'Lane 1 — Content score (`overall_score`):' in template
        assert 'Lane 2 — Structural/procedural blockers (`### Blockers`):' in template
        assert 'Structural blockers gate readiness through `### Blockers`' in template
        assert 'do NOT change the content score' in template

    def test_template_requires_exact_storage_contract(self) -> None:
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
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

    def test_shape_mode_runs_only_design_shape_blockers_not_full_fsdd_scoring(self) -> None:
        # Phase 3, decisions.md "The critic runs after user approval": phase_mode="shape"
        # is a safety net on the design the user already approved, not a full FSDD
        # readiness gate. It must declare phase_mode as an invocation input and must not
        # be able to be confused with validation_mode (a different, detail-act-only axis).
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert '- phase_mode:' in template
        assert 'phase_mode == "shape"' in template
        assert 'Under-Surfaced Decision - BLOCKING' in template
        assert 'Non-Divergent Decision Options - BLOCKING' in template

    def test_shape_mode_stores_nonzero_iteration(self) -> None:
        # STEP S4 must compute a real iteration via get_loop_status, mirroring the
        # post_synthesis path — CriticFeedback defaults iteration=0, and storing that
        # would collide with the "MUST NOT store feedback with iteration=0" contract
        # the rest of the loop machinery relies on.
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert 'SHAPE_ITERATION = SHAPE_LOOP_STATUS.iteration + 1' in template
        assert 'MUST NOT store feedback with iteration=0.' in template

    def test_detail_mode_skips_design_shape_blockers_once_shape_gate_is_settled(self) -> None:
        # decisions.md "the critic runs after user approval": once phase_mode="shape"
        # already ran the Design Shape Evaluation blocker lane and the user approved at
        # the Phase 3 gate, detail mode must not re-raise those same blockers — the
        # detail architect is forbidden from touching Design Shape once the gate is
        # settled, so a blocker raised here would permanently deadlock the loop.
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert 'skip this entire section — raise none of its blockers.' in template

    def test_shape_mode_enforces_od_entry_format(self) -> None:
        # Plan §3 (phase-3-human-gate.md): the OD-NNN | title | Option A | Option B |
        # Recommended format is "enforced by the critic." A missing Recommended line
        # would let Step 6's "accept recommended default" path silently record an empty
        # decision, so this must be a blocker, not just the divergence check.
        tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
        template = generate_phase_critic_template(tools)

        assert 'Malformed Decision Entry - BLOCKING' in template


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
            generate_phase_critic_template(
                create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000)
            ),
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
        critic_tools = create_phase_critic_agent_tools(
            _adapter, phase_length_soft_cap=40000, phase_shape_soft_cap=10000
        )
        template = generate_phase_critic_template(critic_tools)

        assert 'Verify Implementation Plan Reference Semantic Application' in template
        assert 'Citation-only preservation is insufficient' in template
        assert 'Implementation Plan Reference Not Applied - BLOCKING' in template

    def test_phase_architect_template_emits_a_typescript_signature_grammar_alongside_python(self) -> None:
        # Phase 2 (B2/B4): the entry-format spec must branch per language, not describe
        # Python only -- a Python+React phase needs both grammars in the same prompt.
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert '```typescript' in template
        assert 'TypeScript import specifiers are relative paths' in template
        assert 'Component entries' in template
        assert 'Do NOT carry JSX structure, styling, internal helpers' in template

    def test_phase_architect_template_derives_test_naming_from_language_standards_json(self) -> None:
        # B3: TypeScript test naming ("describe/it blocks with clear descriptions")
        # must reach the prompt, and it must be rendered from language_standards.json
        # (F21) rather than a second hand-maintained copy.
        from src.platform.standards_config import language_testing_convention

        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert language_testing_convention('typescript')['naming'] in template
        assert language_testing_convention('python')['naming'] in template

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

    def test_phase_architect_template_uses_invocation_contract_style(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- optional_instructions: Additional user guidance for phase development (if provided)' in template
        assert '### Grouped Markdown Inputs' in template
        assert 'workflow_guidance_markdown' in template
        assert 'Read every project-local path listed under `### Guidance Document Paths`' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template

    def test_phase_architect_template_requires_official_api_doc_research_markers(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'OFFICIAL API DOCUMENTATION RESEARCH PROTOCOL' in template
        assert 'Build an explicit external API inventory before deciding research coverage:' in template
        assert 'Store as EXTERNAL_API_INVENTORY.' in template
        assert 'Provider/API name and official host when discoverable' in template
        assert 'Implementation language/runtime from the project stack' in template
        assert 'official SDK/client library, direct HTTP endpoints, auth, file upload/import' in template
        assert '`apidocs` and `apiintegration`' in template
        assert 'Do NOT browse the web directly from this agent.' in template
        assert 'Do NOT use PascalCase marker variants' in template
        assert (
            'Filename matches are never authoritative for API coverage. Content validation is authoritative.'
            in template
        )
        assert 'Treat `apidocs` and `apiintegration` as topic metadata only' in template
        assert '*apidocs*apiintegration*' not in template
        assert 'filename marker matches are candidate filters only' not in template.lower()
        assert 'official source URLs' in template
        assert 'direct HTTP endpoint contracts' in template
        assert 'request/response schemas or payload contracts' in template
        assert 'payload schemas' in template
        assert 'http endpoints' in template
        assert 'webhooks, errors, versioning' in template
        assert 'SDK/client library vs direct HTTP based on official docs' in template
        assert 'Do not prefer SDKs globally.' in template

    def test_phase_architect_template_requires_structured_synthesize_prompts(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert (
            '- Synthesize: Technologies: <comma-separated technology names>; '
            'Topics: <comma-separated topic keywords>; Query: <specific research request>'
        ) in template
        assert '`Technologies:` MUST be present and non-empty.' in template
        assert '`Topics:` MUST be present and non-empty.' in template
        assert (
            '`Query:` MUST be specific enough for the bp skill to run without inferring technologies or topics.'
            in template
        )
        assert 'Use the `TECH` and `TOPICS` values from the archive scan as the baseline fields' in template
        assert 'Do NOT emit vague free-form synthesis prompts without these structured fields.' in template

        synthesize_lines = [line.strip() for line in template.splitlines() if '- Synthesize:' in line]
        assert synthesize_lines
        for line in synthesize_lines:
            assert 'Technologies:' in line
            assert 'Topics:' in line
            assert 'Query:' in line

    def test_phase_architect_template_uses_structured_api_synthesize_topics(self) -> None:
        architect_tools = create_phase_architect_agent_tools(_adapter)
        template = generate_phase_architect_template(architect_tools)

        assert 'Technologies: {provider_name} API, {implementation_language_runtime}' in template
        assert (
            'Topics: apidocs, apiintegration, official sdk, client library, http endpoints, '
            'authentication, payload schemas, rate limits, retries, pagination, webhooks, errors, versioning'
        ) in template
        assert 'Official API integration docs for {provider_name} in {implementation_language_runtime}' in template
        assert 'include `apidocs` and `apiintegration` in `Topics:` as intent metadata only' in template

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
