"""Tests for command template generation functions."""

from pathlib import Path

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

    def test_codex_roadmap_includes_slot_aware_parallel_policy(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'MAX_ACTIVE_WORKERS =' in template
        assert 'If spawn fails' in template
        assert 'close it' in template

    def test_non_codex_roadmap_excludes_codex_slot_policy(self) -> None:
        coordinator = TemplateCoordinator()
        claude_template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        opencode_template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'MAX_ACTIVE_WORKERS =' not in claude_template
        assert 'MAX_ACTIVE_WORKERS =' not in opencode_template
        assert 'If spawn fails' not in claude_template
        assert 'If spawn fails' not in opencode_template

    def test_non_codex_roadmap_retains_legacy_parallel_wording(self) -> None:
        coordinator = TemplateCoordinator()
        claude_template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        opencode_template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        for template in (claude_template, opencode_template):
            assert 'SINGLE message (parallel invocations)' in template
            assert 'True parallelism requires one message with all invocations.' in template

    def test_roadmap_removes_single_message_parallel_instruction(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'SINGLE message' not in template
        assert 'True parallelism requires one message with all invocations.' not in template

    def test_codex_code_template_includes_close_guidance_in_parallel_policy(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Phase 1 review agents (excluding consolidator)' in template
        assert 'close the completed worker' in template

    def test_non_codex_excludes_codex_slot_policy_across_parallel_sections(self) -> None:
        coordinator = TemplateCoordinator()
        for command in (RespecAICommand.PHASE, RespecAICommand.CODE, RespecAICommand.PATCH):
            claude_template = coordinator.generate_command_template(
                command, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
            )
            opencode_template = coordinator.generate_command_template(
                command, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
            )
            assert 'MAX_ACTIVE_WORKERS =' not in claude_template
            assert 'MAX_ACTIVE_WORKERS =' not in opencode_template
            assert 'If spawn fails' not in claude_template
            assert 'If spawn fails' not in opencode_template

    def test_phase_template_enforces_cost_aware_bp_synthesis_policy(self) -> None:
        coordinator = TemplateCoordinator()
        claude_template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        opencode_template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        for template in (claude_template, opencode_template):
            assert 'MANDATORY COST-AWARE SYNTHESIS POLICY' in template
            assert 'MAX_ACTIVE_BP_WORKERS = 3' in template
            assert 'Do NOT create or execute prompts to hit a quota' in template
            assert 'All launched uncached prompts MUST return BP_PIPELINE_COMPLETE signals.' in template

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

    def test_plan_template_enforces_fail_closed_reference_capture(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'FAIL-CLOSED RULE' in template
        assert 'Plan reference mentioned but no readable source provided.' in template
        assert '.respec-ai/plans/{PLAN_NAME}/references/{REFERENCE_FILENAME}' in template
        assert '/resources/' not in template

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

    def test_phase_template_includes_bp_pipeline_tool_permission(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Task(bp-pipeline)' in template

    def test_phase_template_enforces_fail_closed_task_handoff(self) -> None:
        coordinator = TemplateCoordinator()
        adapters = (ClaudeCodeAdapter(), OpenCodeAdapter(), CodexAdapter())

        for adapter in adapters:
            template = coordinator.generate_command_template(
                RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter
            )
            assert 'MANDATORY TASK HANDOFF PROTOCOL (FAIL-CLOSED)' in template
            assert 'Return "Phase complete" success without attempting Step 9' in template
            assert 'Attempt `respec-task` invocation via Bash/CLI' in template
            assert 'Command handoff path MUST use adapter-rendered orchestration invocation' in template
            assert 'Sanity check orchestration path:' in template
            assert 'Fallback/manual mode does NOT waive Step 9 obligations.' in template
            assert 'IF TASK_INVOCATION_ATTEMPTED == false' in template
            assert 'IF TASK_INVOCATION_METHOD == "shell"' in template

    def test_plan_template_enforces_fail_closed_roadmap_handoff(self) -> None:
        coordinator = TemplateCoordinator()
        adapters = (ClaudeCodeAdapter(), OpenCodeAdapter(), CodexAdapter())

        for adapter in adapters:
            template = coordinator.generate_command_template(
                RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=adapter
            )
            assert 'MANDATORY ROADMAP HANDOFF PROTOCOL (FAIL-CLOSED)' in template
            assert 'Return "Plan complete" success without attempting Step 10' in template
            assert 'Attempt `respec-roadmap` invocation via Bash/CLI' in template
            assert 'IF ROADMAP_INVOCATION_ATTEMPTED == false' in template
            assert 'IF ROADMAP_INVOCATION_METHOD == "shell"' in template
            assert 'roadmap_invocation_method ("orchestration" | "shell"; shell is invalid/non-compliant)' in template

    def test_phase_template_places_task_handoff_after_phase_storage(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        step_8_pos = template.find('### Step 8: Phase Storage')
        step_9_pos = template.find('### Step 9: Automatic Task Generation')
        step_10_pos = template.find('### Step 10: Completion Contract and Final Reporting')

        assert step_8_pos != -1
        assert step_9_pos != -1
        assert step_10_pos != -1
        assert step_8_pos < step_9_pos < step_10_pos

    def test_phase_template_requires_completion_contract_fields(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        assert 'Completion contract (required in final response):' in template
        assert 'phase_file_path' in template
        assert 'phase_status' in template
        assert 'task_invocation_status ("succeeded" | "failed")' in template
        assert 'task_invocation_method ("orchestration" | "shell"; shell is invalid/non-compliant)' in template
        assert 'task_identifier (MCP key when available, else "unavailable")' in template
        assert 'next_action (required when task_invocation_status == "failed")' in template

    def test_phase_template_uses_adapter_owned_phase_command_reference(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert '- `/respec-phase` is the ONLY workflow that runs bp synthesis' not in template
        assert '- `respec-phase` skill is the ONLY workflow that runs bp synthesis' in template

    def test_task_template_fail_fast_on_unresolved_synthesize_prompts(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert '#### Step 2.3: Fail Fast on Unresolved Synthesize Prompts' in template
        assert 'Task planning is blocked until phase-owned synthesis is complete.' in template
        assert 'Do NOT invoke task-planner' in template
        assert 'Do NOT continue to Step 3' in template

    def test_task_template_uses_adapter_owned_task_command_reference(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert '`/respec-task` consumes finalized research artifacts only.' not in template
        assert '`respec-task` skill consumes finalized research artifacts only.' in template

    def test_code_template_override_prompt_has_no_trailing_quote(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Invoke the `respec-code` skill with: `{PLAN_NAME} {PHASE_NAME}`."' not in template
        assert 'To reject:' in template

    def test_task_template_passes_structured_reference_metadata(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'IMPL_PLAN_REFERENCES = []' in template
        assert 'Constraint Precedence Contract' in template
        assert 'TUI Plan Deviation Log' in template

    def test_plan_conversation_allowed_tools_frontmatter_is_comma_separated(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN_CONVERSATION,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'allowed-tools: mcp__exa__web_search_exa, Read' in template
        assert 'allowed-tools: [mcp__exa__web_search_exa, Read]' not in template

    def test_plan_conversation_uses_typed_claude_invocation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN_CONVERSATION,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '/respec-plan [plan-name] [optional: initial context]' in template
        assert 'Invoke the `respec-plan` workflow with:' not in template

    def test_plan_conversation_uses_typed_codex_invocation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN_CONVERSATION,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'Invoke the `respec-plan` skill with: `[plan-name] [optional: initial context]`.' in template

    def test_plan_conversation_removes_non_legacy_claude_labeling(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN_CONVERSATION,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'If Prior Plan Context Was Provided' in template
        assert 'If Claude Plan Context Was Provided' not in template
        assert 'Claude Plan file' not in template

    def test_code_template_excludes_stale_task_targets(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Task(respec-phase-planner)' not in template
        assert 'Task(respec-task-critic)' not in template

    def test_code_template_includes_mode_resolution_precedence(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '### 6.7 Resolve Delivery Intent Policy' in template
        assert 'Deterministic precedence' in template
        assert 'RESOLVED_MODE_SOURCE = "task-policy"' in template
        assert 'RESOLVED_MODE_SOURCE = "phase-override"' in template
        assert 'RESOLVED_MODE_SOURCE = "plan-default"' in template
        assert 'RESOLVED_MODE_SOURCE = "default-MVP"' in template

    def test_code_template_includes_deterministic_user_input_mode_options(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Continue refine in current mode' in template
        assert 'Switch mode and continue refine' in template
        assert 'Finalize now with deferred-risk summary' in template

    def test_code_template_includes_command_owned_commit_orchestration(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 7.4: Phase 1 Iteration Loop (Coder → Reviews → Decision → Commit)' in template
        assert '# D) Phase 1 commit orchestration (command-owned, every pass)' in template
        assert 'Narrow exception: command reads latest feedback only for commit metadata synthesis.' in template
        assert 'Source: review-consolidator CriticFeedback' in template
        assert 'Source: coding-standards-reviewer CriticFeedback' in template
        assert '### 7.5: Standards Finalization Phase' in template
        assert '#### Step 7.5.3: Exit to Completion Gate' in template
        assert '### 8.5 Completion Gate (Mandatory)' in template

    def test_code_template_loads_optional_standards_guides_for_coder(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'GUIDE_FILES = Glob(.respec-ai/config/standards/guides/*.md)' in template
        assert '  - standards_guide: STANDARDS_GUIDE' in template

    def test_code_template_phase1_loop_orders_commit_before_transitions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 7.4: Phase 1 Iteration Loop (Coder → Reviews → Decision → Commit)' in template
        assert '# D) Phase 1 commit orchestration (command-owned, every pass)' in template
        assert '# E) Decision handling after commit' in template
        assert template.index('# D) Phase 1 commit orchestration (command-owned, every pass)') < template.index(
            '# E) Decision handling after commit'
        )
        assert 'Return to Step 7.4 (next loop pass runs coder → reviews → decision → commit).' in template

    def test_code_template_phase1_commit_subject_is_checkpoint_only(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'COMMIT_SUBJECT = "[WIP] {PHASE_NAME} [Phase 1 iter {CODING_ITERATION}]"' in template
        assert 'COMMIT_SUBJECT = "feat: complete {PHASE_NAME}"' not in template
        assert 'git commit --allow-empty --no-verify -F - <<' in template

    def test_code_template_uses_mandatory_precommit_completion_gate(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'PRECOMMIT_EXIT_CODE = run: pre-commit run -a' in template
        assert 'Finalization is non-compliant until hooks pass.' in template
        assert 'git commit --allow-empty --no-verify -F - <<' in template
        assert 'Append in deterministic order: Test, Type check, Lint' not in template

    def test_codex_code_template_prefers_commit_skill_in_commit_orchestration(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert '$Commit' in template
        assert 'git commit --no-verify -F - <<' in template

    def test_task_template_excludes_stale_create_task_target(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Task(respec-create-task)' not in template

    def test_patch_template_requires_upfront_mode_and_code_quality_core_reviewer(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 1.2: Capture Execution Mode (MANDATORY)' in template
        assert 'Header: "Patch Mode"' in template
        assert (
            'ACTIVE_REVIEWERS = ["automated-quality-checker", "spec-alignment-reviewer", "code-quality-reviewer"]'
            in template
        )
        assert 'Task(respec-code-quality-reviewer)' in template

    def test_patch_template_includes_command_owned_commit_orchestration(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 5.3: Phase 1 Iteration Loop (Coder -> Reviews -> Decision -> Commit)' in template
        assert '# D) Phase 1 commit orchestration (command-owned, every pass)' in template
        assert 'Narrow exception: command reads latest feedback only for commit metadata synthesis.' in template
        assert 'Source: review-consolidator CriticFeedback' in template
        assert 'Source: coding-standards-reviewer CriticFeedback' in template
        assert '#### Step 6.5.3: Exit to Completion Gate' in template
        assert '### 6.7 Completion Gate (Mandatory)' in template

    def test_patch_template_loads_optional_standards_guides_for_coder(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'GUIDE_FILES = Glob(.respec-ai/config/standards/guides/*.md)' in template
        assert '  - standards_guide: STANDARDS_GUIDE' in template

    def test_patch_template_phase1_loop_orders_commit_before_transitions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 5.3: Phase 1 Iteration Loop (Coder -> Reviews -> Decision -> Commit)' in template
        assert '# D) Phase 1 commit orchestration (command-owned, every pass)' in template
        assert '# E) Decision handling after commit' in template
        assert template.index('# D) Phase 1 commit orchestration (command-owned, every pass)') < template.index(
            '# E) Decision handling after commit'
        )
        assert 'Return to Step 5.3 (next loop pass runs coder -> reviews -> decision -> commit).' in template

    def test_patch_template_phase1_commit_subject_is_checkpoint_only(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'COMMIT_SUBJECT = "[WIP] patch {PHASE_NAME} [Phase 1 iter {CODING_ITERATION}]"' in template
        assert 'COMMIT_SUBJECT = "fix: complete {CHANGE_DESCRIPTION}"' not in template
        assert 'git commit --allow-empty --no-verify -F - <<' in template

    def test_patch_template_uses_mandatory_precommit_completion_gate(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'PRECOMMIT_EXIT_CODE = run: pre-commit run -a' in template
        assert 'Finalization is non-compliant until hooks pass.' in template
        assert 'git commit --allow-empty --no-verify -F - <<' in template
        assert 'Append in deterministic order: Test, Type check, Lint' not in template

    def test_guideline_exception_matches_code_and_patch_templates(self) -> None:
        guidelines = Path('docs/AGENT_DEVELOPMENT_GUIDELINES.md').read_text(encoding='utf-8')
        assert 'Narrow Exception: Commit Metadata Synthesis in `respec-code` / `respec-patch`' in guidelines
        assert 'NOT passed to specialized agents as input parameters' in guidelines
        assert 'does NOT override MCP decision authority' in guidelines

        coordinator = TemplateCoordinator()
        code_template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        patch_template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        exception_phrase = 'Narrow exception: command reads latest feedback only for commit metadata synthesis.'
        assert exception_phrase in code_template
        assert exception_phrase in patch_template

    def test_standards_command_template_is_render_first(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.STANDARDS,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [optional: language|all]' in template
        assert 'description: Render standards guides from canonical TOML templates' in template
        assert 'This command MUST NOT edit canonical TOML files.' in template
        assert 'If RAW_ARGS[0] == "render", treat RAW_ARGS[1] as target.' in template
        assert 'TARGET = normalized lowercase target token (optional: language or "all")' in template
        assert (
            'standards_languages_missing: no language TOML files found under .respec-ai/config/standards/' in template
        )
        assert 'IF TARGET is missing:' in template
        assert 'MUST call AskUserQuestion to select one language or "all".' in template
        assert 'MUST NOT infer or auto-select a default target, even when only one language exists.' in template
        assert (
            'standards_target_selection_unavailable: missing AskUserQuestion tool; cannot continue without explicit target selection.'
            in template
        )
        assert "standards_language_invalid: target '{TARGET}' not found; available={AVAILABLE_LANGUAGES}." in template
        assert 'TARGET_LANGUAGES = AVAILABLE_LANGUAGES' in template
        assert 'AUTHOR FLOW' not in template
        assert 'Standards template updated for: {TARGET_LANGUAGES}' not in template
        assert 'TARGET_GUIDE = .respec-ai/config/standards/guides/{LANGUAGE}.md' in template
        assert 'If a section is missing in TOML, omit it from the guide (do not invent values)' in template
        assert 'Canonical source remains: .respec-ai/config/standards/{LANGUAGE}.toml for each language' in template
