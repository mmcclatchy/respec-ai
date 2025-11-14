"""Tests for agent template generation functions."""

from services.platform.models import CreateSpecAgentTools, PlanRoadmapAgentTools
from services.templates.agents.create_spec import generate_create_spec_template
from services.templates.agents.roadmap import generate_roadmap_template
from services.templates.agents.roadmap_critic import generate_roadmap_critic_template


class TestPlanRoadmapTemplate:
    def test_template_structure(self) -> None:
        tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        template = generate_roadmap_template(tools)

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: specter-roadmap' in template
        assert 'description:' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template

        # Check MCP tools section
        assert '- mcp__specter__get_project_plan_markdown' in template
        assert '- mcp__specter__add_spec' in template
        assert '- mcp__specter__list_specs' in template

        # Check agent identity
        assert 'You are a' in template
        assert 'roadmap' in template.lower()

        # Check input/output sections
        assert 'INPUTS:' in template
        assert 'TASKS:' in template
        assert 'OUTPUTS:' in template or 'OUTPUT FORMAT:' in template

    def test_template_follows_imperative_pattern(self) -> None:
        tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        template = generate_roadmap_template(tools)

        # Should contain imperative verbs
        imperative_verbs = ['Parse', 'Break', 'Extract', 'Create', 'Establish', 'Define']
        has_imperative = any(verb in template for verb in imperative_verbs)
        assert has_imperative, 'Template should contain imperative instructions'

    def test_template_no_threshold_references(self) -> None:
        tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        template = generate_roadmap_template(tools)

        # Should not contain threshold percentages or scores
        threshold_terms = ['85%', '90%', 'threshold', 'score', '%']
        for term in threshold_terms:
            assert term not in template, f'Template should not contain threshold reference: {term}'

    def test_template_includes_error_handling(self) -> None:
        tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        template = generate_roadmap_template(tools)

        assert 'ERROR HANDLING' in template or 'Error Handling' in template


class TestRoadmapCriticTemplate:
    def test_template_structure(self) -> None:
        template = generate_roadmap_critic_template()

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: specter-roadmap-critic' in template
        assert 'description:' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template

        # Check MCP tools for data retrieval and feedback storage
        assert '- mcp__specter__get_roadmap_markdown' in template
        assert '- mcp__specter__get_feedback' in template
        assert '- mcp__specter__store_critic_feedback' in template

    def test_template_includes_critic_feedback_format(self) -> None:
        template = generate_roadmap_critic_template()

        # Should include CriticFeedback structure
        assert '# Critic Feedback: ROADMAP-CRITIC' in template
        assert 'Overall Score' in template
        assert 'Assessment Summary' in template
        assert 'Issues and Recommendations' in template

    def test_template_includes_fsdd_criteria(self) -> None:
        template = generate_roadmap_critic_template()

        # Should reference FSDD framework
        assert 'FSDD' in template or '12-point' in template

        # Should include key assessment areas
        assessment_areas = ['Phase Scoping', 'Dependency', 'Implementation Readiness']
        for area in assessment_areas:
            assert area in template or area.lower() in template.lower()

    def test_template_no_threshold_references(self) -> None:
        template = generate_roadmap_critic_template()

        # Should not contain specific threshold values
        threshold_terms = ['85%', '90%', 'threshold configured']
        for term in threshold_terms:
            assert term not in template, f'Template should not contain threshold reference: {term}'


class TestCreateSpecTemplate:
    def test_template_structure(self) -> None:
        tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )
        template = generate_create_spec_template(tools)

        # Check YAML frontmatter
        assert '---' in template
        assert 'name: specter-create-spec' in template
        assert 'description:' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template

    def test_template_includes_mcp_tools(self) -> None:
        tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )
        template = generate_create_spec_template(tools)

        # Should include MCP tools
        mcp_tools = ['get_roadmap', 'add_spec', 'store_spec']
        has_mcp_tool = any(tool in template for tool in mcp_tools)
        assert has_mcp_tool, 'Template should include MCP tools for roadmap operations'

    def test_template_supports_parallel_execution(self) -> None:
        tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )
        template = generate_create_spec_template(tools)

        # Should mention individual spec creation (not multiple)
        assert 'Project ID' in template
        assert 'Spec Name' in template
        assert 'Phase Context' in template

    def test_template_includes_initialspec_creation(self) -> None:
        tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )
        template = generate_create_spec_template(tools)

        # Should reference InitialSpec
        assert 'InitialSpec' in template


class TestTemplateConsistency:
    def test_all_templates_use_sonnet(self) -> None:
        plan_tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        spec_tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )

        templates = [
            generate_roadmap_template(plan_tools),
            generate_roadmap_critic_template(),
            generate_create_spec_template(spec_tools),
        ]

        for template in templates:
            assert 'model: sonnet' in template

    def test_all_templates_have_required_sections(self) -> None:
        plan_tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        spec_tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )

        templates = [
            generate_roadmap_template(plan_tools),
            generate_roadmap_critic_template(),
            generate_create_spec_template(spec_tools),
        ]

        required_sections = ['name:', 'description:', 'INPUTS:', 'TASKS:']

        for template in templates:
            for section in required_sections:
                assert section in template, f'Template missing required section: {section}'

    def test_no_template_contains_behavioral_descriptions(self) -> None:
        plan_tools = PlanRoadmapAgentTools(create_spec_external='mcp__specter__add_spec')
        spec_tools = CreateSpecAgentTools(
            create_spec_tool='mcp__specter__add_spec',
            get_spec_tool='mcp__specter__get_spec',
            update_spec_tool='mcp__specter__update_spec',
        )

        templates = [
            generate_roadmap_template(plan_tools),
            generate_roadmap_critic_template(),
            generate_create_spec_template(spec_tools),
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
