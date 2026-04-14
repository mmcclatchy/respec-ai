"""Tests for agent template generation functions."""

from src.platform.models import PlatformType
from src.platform.tui_adapters import ClaudeCodeAdapter

from src.platform.template_helpers import (
    create_create_phase_agent_tools,
    create_patch_planner_agent_tools,
    create_phase_architect_agent_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_task_plan_critic_agent_tools,
    create_task_planner_agent_tools,
)
from src.platform.templates.agents import (
    generate_create_phase_template,
    generate_patch_planner_template,
    generate_phase_architect_template,
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
        assert 'model: sonnet' in template
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


class TestTaskPlanCriticTemplate:
    def test_template_enforces_tui_plan_reference_validation(self) -> None:
        tools = create_task_plan_critic_agent_tools(_adapter)
        template = generate_task_plan_critic_template(tools)

        assert 'MANDATORY TUI PLAN REFERENCE VALIDATION' in template
        assert '.respec-ai/plans/{PLAN_NAME}/references/' in template
        assert '(per plan reference: ...)' in template
        assert 'TUI Plan Deviation Log' in template
        assert 'cap score at 80' in template


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


class TestTemplateConsistency:
    def test_template_models(self) -> None:
        roadmap_tools = create_roadmap_agent_tools(_adapter)
        critic_tools = create_roadmap_critic_agent_tools(_adapter)
        platform_tools = ['Write(.respec-ai/plans/*/phases/*.md)', 'Read', 'Edit']
        create_phase_tools = create_create_phase_agent_tools(_adapter, platform_tools, PlatformType.MARKDOWN)

        # Roadmap uses opus (creative synthesis — architectural decomposition)
        assert 'model: opus' in generate_roadmap_template(roadmap_tools)

        # Critic and create-phase use sonnet (structured evaluation / extraction)
        sonnet_templates = [
            generate_roadmap_critic_template(critic_tools),
            generate_create_phase_template(create_phase_tools),
        ]
        for template in sonnet_templates:
            assert 'model: sonnet' in template

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

        required_sections = ['name:', 'description:', 'INPUTS:', 'TASKS:']

        for template in templates:
            for section in required_sections:
                assert section in template, f'Template missing required section: {section}'

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

    def test_task_planner_template_accepts_structured_reference_inputs(self) -> None:
        task_planner_tools = create_task_planner_agent_tools(_adapter)
        template = generate_task_planner_template(task_planner_tools)
        assert '- impl_plan_references: Optional structured references' in template
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
        assert '#### Execution Intent Policy' in template
        assert '#### Deferred Risk Register' in template
        assert 'patch-mode-selection' in template
