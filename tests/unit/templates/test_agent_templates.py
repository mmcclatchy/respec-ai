"""Tests for agent template generation functions."""

from src.platform.models import PlatformType
from src.platform.tui_adapters import ClaudeCodeAdapter

from src.platform.template_helpers import (
    create_analyst_critic_agent_tools,
    create_create_phase_agent_tools,
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
        assert 'TUI Plan Usage Penalty (BLOCKING' in template
        assert 'cap overall score at 80' in template

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


class TestTaskPlanCriticTemplate:
    def test_template_enforces_tui_plan_reference_validation(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'MANDATORY TUI PLAN REFERENCE VALIDATION' in template
        assert '.respec-ai/plans/{PLAN_NAME}/references/' in template
        assert '(per plan reference: ...)' in template
        assert 'TUI Plan Deviation Log' in template
        assert 'cap score at 80' in template

    def test_template_uses_single_workflow_guidance_contract(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'workflow_guidance_markdown:' in template
        assert 'optional_context:' not in template
        assert 'request_brief:' not in template
        assert 'Workflow Guidance Alignment' in template
        assert '## Invocation Contract' in template
        assert '## Workflow Guidance' in template


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
        assert 'API_RESEARCH_FRESHNESS_PENALTY' in template

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
            'HAS_VALID_BP_READ_COVERAGE = any VALID_BP_READ_PATHS item contains api_name OR API_SLUG_TOKEN' in template
        )
        assert 'HAS_SYNTH_COVERAGE = any SYNTHESIZE_LINES item contains api_name OR API_SLUG_TOKEN' in template
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


class TestPlanCriticTemplate:
    def test_template_uses_invocation_contract_style(self) -> None:
        tools = create_plan_critic_agent_tools(_adapter)
        template = generate_plan_critic_template(tools)

        assert '## Invocation Contract' in template
        assert '### Scalar Inputs' in template
        assert '- plan_name: Plan name for MCP plan retrieval' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert '### Retrieved Context (Not Invocation Inputs)' in template


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
        assert 'Exception: If plan references exist, you MAY add only:' in template
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

    def test_patch_planner_template_requires_execution_intent_and_deferred_risks(self) -> None:
        patch_planner_tools = create_patch_planner_agent_tools(_adapter)
        template = generate_patch_planner_template(patch_planner_tools)
        assert '- execution_mode: User-selected mode from respec-patch command' in template
        assert '## Invocation Contract' in template
        assert '#### Execution Intent Policy' in template
        assert '#### Deferred Risk Register' in template
        assert 'patch-mode-selection' in template

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

    def test_plan_analyst_documents_only_loop_id_as_invocation_input(self) -> None:
        tools = create_plan_analyst_agent_tools(_adapter)
        template = generate_plan_analyst_template(tools)

        assert '## Invocation Contract' in template
        assert '- loop_id: Loop ID provided by Main Agent for MCP plan retrieval' in template
        assert '### Grouped Markdown Inputs' in template
        assert '- None' in template
        assert 'Business context, requirements, success criteria, and constraints embedded' in template
