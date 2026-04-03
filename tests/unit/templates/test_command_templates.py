"""Tests for command template generation functions."""

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter


class TestPlanRoadmapRespecAICommand:
    def test_template_has_required_tools(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Check YAML frontmatter tools (comma-separated format)
        assert 'Task(respec-roadmap)' in template
        assert 'Task(respec-roadmap-critic)' in template
        assert 'Task(respec-create-phase)' in template
        assert 'mcp__linear-server__' in template  # Should contain Linear tools
        assert 'mcp__respec-ai__initialize_refinement_loop' in template
        assert 'mcp__respec-ai__decide_loop_next_action' in template

    def test_template_includes_required_yaml_sections(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        assert '---' in template
        assert 'allowed-tools:' in template
        assert 'argument-hint:' in template
        assert 'description:' in template

    def test_template_is_orchestration_focused(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

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
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Should not contain threshold percentages or direct threshold logic
        threshold_terms = ['85%', '90%', 'quality gate', 'threshold:', 'threshold =', 'if score >']
        for term in threshold_terms:
            assert term not in template, f'Template should not reference thresholds: {term}'

    def test_template_includes_parallel_phase_creation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Should include create-phase agent and parallel coordination
        assert 'Task(respec-create-phase)' in template
        assert 'parallel' in template.lower() or 'concurrent' in template.lower()

    def test_template_includes_mcp_action_handling(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Should include MCP action patterns
        mcp_actions = ['refine', 'complete', 'user_input']
        for action in mcp_actions:
            assert action in template, f'Template should handle MCP action: {action}'

    def test_template_size_is_reasonable(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        lines = template.split('\n')
        line_count = len(lines)

        # Target is 150-200 lines, allow some flexibility
        assert 100 <= line_count <= 450, f'Template should be 100-450 lines, got {line_count}'

    def test_template_has_no_agent_behavioral_instructions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

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
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Should include error handling
        error_handling_terms = ['Error Handling', 'ERROR', 'failure', 'graceful']
        has_error_handling = any(term in template for term in error_handling_terms)
        assert has_error_handling, 'Template should include error handling patterns'

    def test_template_maintains_platform_tool_injection(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        # Should properly inject platform tools
        assert 'mcp__linear-server__' in template  # Should contain Linear tools


class TestCrossPlatformInvocationRendering:
    def test_claude_code_uses_invoke_syntax_for_roadmap(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'Invoke: respec-roadmap' in template
        assert 'CALL task:' not in template

    def test_opencode_uses_task_call_syntax_for_roadmap(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'CALL task:' in template
        assert 'subagent_type: "respec-roadmap"' in template
        assert 'Invoke: respec-roadmap' not in template

    def test_claude_code_uses_invoke_syntax_for_task(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'Invoke: respec-task-planner' in template
        assert 'Invoke: respec-task-plan-critic' in template

    def test_opencode_uses_task_call_syntax_for_task(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'subagent_type: "respec-task-planner"' in template
        assert 'subagent_type: "respec-task-plan-critic"' in template

    def test_claude_code_patch_uses_planning_loop_id(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'PLANNING_LOOP_ID' in template
        # Ensure none of the pre-computed invocations reference TASK_LOOP_ID
        # (patch uses PLANNING_LOOP_ID throughout for task retrieval)
        invoke_section = template[template.find('#### Step 3.3') :]
        assert 'task_loop_id: TASK_LOOP_ID' not in invoke_section

    def test_opencode_patch_embeds_planning_loop_id_in_prompt(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'subagent_type: "respec-patch-planner"' in template
        assert '- task_loop_id: PLANNING_LOOP_ID' in template

    def test_claude_code_plan_conversation_uses_slash_syntax(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert '/respec-plan-conversation' in template

    def test_opencode_plan_conversation_uses_inline_guide(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        # OpenCode replaces the invocation block with inline conversation guide stages
        assert 'Stage 1: Vision and Context Discovery' in template
        # The invocation block should NOT contain bash/slash syntax
        assert '```bash\n/respec-plan-conversation' not in template

    def test_codex_plan_uses_skill_invocation_for_roadmap_handoff(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Invoke the `respec-roadmap` skill' in template
        assert '```bash\n/respec-roadmap {{PLAN_NAME}}' not in template

    def test_plan_uses_tui_agnostic_plan_reference_marker(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'Plan Reference: {PLAN_REFERENCE_FILE}' in template
        assert 'Claude Plan: {CLAUDE_PLAN_FILE}' not in template

    def test_claude_code_phase_to_task_uses_slash_syntax(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert '/respec-task' in template

    def test_opencode_phase_to_task_uses_suggestion_text(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'respec-task' in template

    def test_plan_conversation_allowed_tools_frontmatter_is_comma_separated(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN_CONVERSATION,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'allowed-tools: mcp__exa__web_search_exa, Read' in template
        assert 'allowed-tools: [mcp__exa__web_search_exa, Read]' not in template

    def test_code_template_excludes_stale_task_targets(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Task(respec-phase-planner)' not in template
        assert 'Task(respec-task-critic)' not in template

    def test_task_template_excludes_stale_create_task_target(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Task(respec-create-task)' not in template
