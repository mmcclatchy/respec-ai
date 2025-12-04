"""Tests for command template generation functions."""

from services.platform.platform_selector import PlatformType
from services.platform.template_coordinator import TemplateCoordinator
from services.platform.tool_enums import CommandTemplate


class TestPlanRoadmapCommandTemplate:
    def test_template_has_required_tools(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Check YAML frontmatter tools (comma-separated format)
        assert 'Task(spec-ai-roadmap)' in template
        assert 'Task(spec-ai-roadmap-critic)' in template
        assert 'Task(spec-ai-create-spec)' in template
        assert 'mcp__linear-server__' in template  # Should contain Linear tools
        assert 'mcp__spec-ai__initialize_refinement_loop' in template
        assert 'mcp__spec-ai__decide_loop_next_action' in template

    def test_template_includes_required_yaml_sections(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        assert '---' in template
        assert 'allowed-tools:' in template
        assert 'argument-hint:' in template
        assert 'description:' in template

    def test_template_is_orchestration_focused(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should contain orchestration keywords
        orchestration_terms = ['Orchestration', 'Workflow', 'Coordination']
        has_orchestration = any(term in template for term in orchestration_terms)
        assert has_orchestration

        # Should NOT contain detailed implementation guidance
        detailed_implementation = [
            'Primary Tasks:',
            '1. Analyze the strategic plan for technical feasibility',
            'Expected Output Format:',
            'Step-by-step implementation sequence',
        ]
        for detail in detailed_implementation:
            assert detail not in template, f'Template should not contain detailed implementation: {detail}'

    def test_template_has_no_quality_thresholds(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should not contain threshold percentages or direct threshold logic
        threshold_terms = ['85%', '90%', 'quality gate', 'threshold:', 'threshold =', 'if score >']
        for term in threshold_terms:
            assert term not in template, f'Template should not reference thresholds: {term}'

    def test_template_includes_parallel_spec_creation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should include create-spec agent and parallel coordination
        assert 'Task(spec-ai-create-spec)' in template
        assert 'parallel' in template.lower() or 'concurrent' in template.lower()

    def test_template_includes_mcp_action_handling(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should include MCP action patterns
        mcp_actions = ['refine', 'complete', 'user_input']
        for action in mcp_actions:
            assert action in template, f'Template should handle MCP action: {action}'

    def test_template_size_is_reasonable(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        lines = template.split('\n')
        line_count = len(lines)

        # Target is 150-200 lines, allow some flexibility
        assert 100 <= line_count <= 450, f'Template should be 100-450 lines, got {line_count}'

    def test_template_has_no_agent_behavioral_instructions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should not contain agent behavioral instructions
        behavioral_instructions = [
            'Primary Tasks:',
            '1. Design technical architecture',
            '2. Analyze archive scan results',
            'You will analyze',
            'Your role is to',
            'Consider the implementation',
        ]

        for instruction in behavioral_instructions:
            assert instruction not in template, f'Template should not contain behavioral instruction: {instruction}'

    def test_template_includes_error_handling(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should include error handling
        error_handling_terms = ['Error Handling', 'ERROR', 'failure', 'graceful']
        has_error_handling = any(term in template for term in error_handling_terms)
        assert has_error_handling, 'Template should include error handling patterns'

    def test_template_maintains_platform_tool_injection(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(CommandTemplate.ROADMAP, PlatformType.LINEAR)

        # Should properly inject platform tools
        assert 'mcp__linear-server__' in template  # Should contain Linear tools
