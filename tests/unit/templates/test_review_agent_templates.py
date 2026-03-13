from src.platform.template_helpers import (
    create_automated_quality_checker_agent_tools,
    create_backend_api_reviewer_agent_tools,
    create_coder_agent_tools,
    create_database_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
    create_review_consolidator_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
)
from src.platform.templates.agents import (
    generate_automated_quality_checker_template,
    generate_backend_api_reviewer_template,
    generate_coder_template,
    generate_database_reviewer_template,
    generate_frontend_reviewer_template,
    generate_infrastructure_reviewer_template,
    generate_review_consolidator_template,
    generate_spec_alignment_reviewer_template,
)


class TestAutomatedQualityCheckerTemplate:
    def test_template_structure(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        assert '---' in template
        assert 'name: respec-automated-quality-checker' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_project_configuration(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        assert 'PROJECT CONFIGURATION' in template
        assert '.respec-ai/config/stack.md' in template
        assert '.respec-ai/config/*.md' in template

    def test_template_includes_scoring(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        assert 'Tests Passing' in template
        assert 'Type Checking' in template
        assert 'Linting' in template
        assert 'Coverage' in template
        assert '70' in template  # 70 points total

    def test_template_has_mcp_tools(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        assert 'mcp__respec-ai__get_document' in template
        assert 'mcp__respec-ai__store_review_section' in template

    def test_template_no_hardcoded_python_tools(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        # Should not contain hardcoded tool names as commands
        assert 'Run pytest' not in template
        assert 'Run mypy' not in template
        assert 'Run ruff' not in template


class TestSpecAlignmentReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_spec_alignment_reviewer_agent_tools()
        template = generate_spec_alignment_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-spec-alignment-reviewer' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_alignment_scoring(self) -> None:
        tools = create_spec_alignment_reviewer_agent_tools()
        template = generate_spec_alignment_reviewer_template(tools)

        assert 'Phase Alignment' in template
        assert 'Requirements' in template
        assert '30' in template  # 30 points total


class TestFrontendReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_frontend_reviewer_agent_tools()
        template = generate_frontend_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-frontend-reviewer' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_accessibility(self) -> None:
        tools = create_frontend_reviewer_agent_tools()
        template = generate_frontend_reviewer_template(tools)

        assert 'accessibility' in template.lower() or 'Accessibility' in template


class TestBackendApiReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_backend_api_reviewer_agent_tools()
        template = generate_backend_api_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-backend-api-reviewer' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_api_design(self) -> None:
        tools = create_backend_api_reviewer_agent_tools()
        template = generate_backend_api_reviewer_template(tools)

        assert 'API' in template
        assert 'validation' in template.lower() or 'Validation' in template


class TestDatabaseReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_database_reviewer_agent_tools()
        template = generate_database_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-database-reviewer' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_schema_review(self) -> None:
        tools = create_database_reviewer_agent_tools()
        template = generate_database_reviewer_template(tools)

        assert 'Schema' in template or 'schema' in template
        assert 'Migration' in template or 'migration' in template


class TestInfrastructureReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_infrastructure_reviewer_agent_tools()
        template = generate_infrastructure_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-infrastructure-reviewer' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_container_review(self) -> None:
        tools = create_infrastructure_reviewer_agent_tools()
        template = generate_infrastructure_reviewer_template(tools)

        assert 'Docker' in template or 'container' in template.lower()


class TestReviewConsolidatorTemplate:
    def test_template_structure(self) -> None:
        tools = create_review_consolidator_agent_tools()
        template = generate_review_consolidator_template(tools)

        assert '---' in template
        assert 'name: respec-review-consolidator' in template
        assert 'model: sonnet' in template
        assert 'INPUTS:' in template
        assert 'TASKS:' in template

    def test_template_includes_consolidation_workflow(self) -> None:
        tools = create_review_consolidator_agent_tools()
        template = generate_review_consolidator_template(tools)

        assert 'CONSOLIDATION WORKFLOW' in template
        assert 'SCORING RULES' in template

    def test_template_includes_critic_feedback_format(self) -> None:
        tools = create_review_consolidator_agent_tools()
        template = generate_review_consolidator_template(tools)

        assert '# Critic Feedback: REVIEW-CONSOLIDATOR' in template
        assert 'Overall Score' in template
        assert 'Assessment Summary' in template

    def test_template_has_mcp_tools(self) -> None:
        tools = create_review_consolidator_agent_tools()
        template = generate_review_consolidator_template(tools)

        assert 'mcp__respec-ai__store_critic_feedback' in template
        assert 'mcp__respec-ai__list_review_sections' in template


class TestReviewAgentConsistency:
    def test_all_review_agents_use_sonnet(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools()),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools()),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools()),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools()),
            generate_database_reviewer_template(create_database_reviewer_agent_tools()),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools()),
            generate_review_consolidator_template(create_review_consolidator_agent_tools()),
        ]

        for template in templates:
            assert 'model: sonnet' in template

    def test_all_review_agents_have_required_sections(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools()),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools()),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools()),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools()),
            generate_database_reviewer_template(create_database_reviewer_agent_tools()),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools()),
            generate_review_consolidator_template(create_review_consolidator_agent_tools()),
        ]

        for template in templates:
            assert 'name:' in template
            assert 'description:' in template
            assert 'INPUTS:' in template
            assert 'TASKS:' in template

    def test_no_review_agent_contains_behavioral_descriptions(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools()),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools()),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools()),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools()),
            generate_database_reviewer_template(create_database_reviewer_agent_tools()),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools()),
            generate_review_consolidator_template(create_review_consolidator_agent_tools()),
        ]

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


class TestCoderTemplateConfig:
    def test_coder_template_has_project_configuration(self) -> None:
        tools = create_coder_agent_tools(
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'PROJECT CONFIGURATION' in template
        assert '.respec-ai/config/stack.md' in template
        assert '.respec-ai/config/*.md' in template

    def test_coder_template_no_pseudocode_remains(self) -> None:
        tools = create_coder_agent_tools(
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'TOOLS.test_runner' not in template
        assert 'TOOLS.test_command' not in template
        assert 'CONFIG = Read' not in template
        assert 'TOOLING[LANGUAGE]' not in template

    def test_quality_checker_template_no_pseudocode_remains(self) -> None:
        tools = create_automated_quality_checker_agent_tools()
        template = generate_automated_quality_checker_template(tools)

        assert 'TOOLS.test_runner' not in template
        assert 'CONFIG = Read' not in template
        assert 'TOOLING[LANGUAGE]' not in template
