"""Tests for command template generation functions."""

import re
from pathlib import Path

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter


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

_COMMAND_ACTION_SECTION_TOKENS = (
    '## Workflow Steps',
    '## How to Conduct This Conversation',
    '## Step ',
    '### Step ',
    '#### Step ',
    'MANDATORY ',
    'FAIL-CLOSED RULE',
    'Strategic plan creation process:',
    'Option gating rules:',
    '### Wait for user response and process decision',
    '## Error Handling',
    '## Quality Assessment',
    '## Research Integration',
    '### Final Step',
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
        elif stripped.startswith('VIOLATION:') or stripped.startswith('FAIL-CLOSED RULE'):
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


def test_actionable_section_extraction_includes_text_fences_but_skips_markdown_examples() -> None:
    template = """## Workflow Steps
```text
This should be flagged.
```
### Final Step
```markdown
This should stay ignored.
```
"""

    actionable = _extract_actionable_sections(template, _COMMAND_ACTION_SECTION_TOKENS)

    assert 'This should be flagged.' in actionable
    assert 'This should stay ignored.' not in actionable


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
        assert 100 <= line_count <= 500, f'Template should be 100-500 lines, got {line_count}'

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
        assert '## Codex Subagent Guardrail' in template
        assert 'NEVER invoke a subagent with forked context.' in template
        assert template.index('## Codex Subagent Guardrail') < template.index('## Workflow Steps')
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
        assert '## Codex Subagent Guardrail' not in claude_template
        assert '## Codex Subagent Guardrail' not in opencode_template

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
        assert '## Codex Subagent Guardrail' in template
        assert 'Phase 1 review agents' in template
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
            assert 'MANDATORY BP OUTPUT VALIDATION GATE' in template
            assert "BP_PATH_REGEX = '(\\.best-practices/[A-Za-z0-9._/-]+\\.md)'" in template
            assert 'PATH_REGEX = BP_PATH_REGEX' in template
            assert 'IF len(CANDIDATE_PATHS) != 1:' in template

    def test_claude_code_patch_uses_explicit_task_loop_alias(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'PLANNING_LOOP_ID' in template
        assert 'TASK_LOOP_ID = PLANNING_LOOP_ID' in template
        assert '- Alias: TASK_LOOP_ID = PLANNING_LOOP_ID for respec-patch amendment tasks' in template
        invoke_section = template[template.find('#### Step 3.3') :]
        assert 'Invoke: respec-patch-planner' in invoke_section
        assert 'Invoke: respec-task-plan-critic' in invoke_section
        assert 'Invoke: respec-coder' in invoke_section
        assert 'task_loop_id: PLANNING_LOOP_ID' in invoke_section
        assert 'task_loop_id: TASK_LOOP_ID' in invoke_section
        assert 'TASK_MARKDOWN = mcp__respec-ai__get_document(doc_type="task", loop_id={TASK_LOOP_ID})' in template

    def test_opencode_patch_embeds_planning_loop_id_in_prompt(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )
        assert 'subagent_type: "respec-patch-planner"' in template
        assert '- task_loop_id: PLANNING_LOOP_ID' in template
        assert '- task_loop_id: TASK_LOOP_ID' in template

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

    def test_plan_template_gates_acceptance_when_blockers_active(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'BLOCKERS_ACTIVE = len(BLOCKERS_LIST) > 0' in template
        assert 'IF BLOCKERS_ACTIVE and not BLOCKER_STAGNATION:' in template
        assert 'Auto-refining plan until blockers clear or stagnation is detected.' in template
        assert 'Do NOT prompt user in this state' in template
        assert 'Please choose your preferred option (1 or 2)' not in template
        assert 'Cannot accept while structural blockers are active. Choose 1 or 2.' not in template

    def test_code_template_does_not_reference_patch_style_planning_loop_tools(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        assert 'initialize_planning_loop' not in template
        assert 'decide_planning_action' not in template

    def test_generated_commands_use_completed_loop_status_token(self) -> None:
        coordinator = TemplateCoordinator()
        commands = (
            RespecAICommand.PHASE,
            RespecAICommand.TASK,
            RespecAICommand.ROADMAP,
            RespecAICommand.CODE,
            RespecAICommand.PATCH,
            RespecAICommand.COMMIT,
        )

        for command in commands:
            template = coordinator.generate_command_template(
                command,
                PlatformType.LINEAR,
                tui_adapter=CodexAdapter(),
            )
            assert '"completed"' in template, f'{command.value} should branch on completed'
            assert '"complete"' not in template, f'{command.value} should not branch on complete'

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

    def test_phase_template_includes_bp_tool_permission(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Task(bp)' in template

    def test_phase_template_uses_bp_public_entrypoint_in_step_7_5(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Task(bp):' in template
        assert 'IF "Task(bp)" is NOT present in allowed tools OR runtime cannot invoke bp:' in template
        assert 'BP_PIPELINE_COMPLETE' not in template

    def test_phase_template_derives_api_based_synthesis_queue(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'SUB-STEP 2.1: Detect external APIs/services from phase content' in template
        assert "BP_PATH_REGEX = '(\\.best-practices/[A-Za-z0-9._/-]+\\.md)'" in template
        assert 'EXISTING_READ_BLOCKS' in template
        assert 'SYNTHESIZE_PROMPT_METADATA' in template
        assert 'EXISTING_BP_READ_PATHS = []' in template
        assert 'APIS_WITH_VALID_BP_DOCS = []' in template
        assert 'APIS_MISSING_BP_DOCS = []' in template
        assert 'VALIDATED_API_DOCS = []' in template
        assert 'METADATA_MATCHES_API' in template
        assert 'METADATA_MATCHES_RUNTIME' in template
        assert 'CONTENT_MATCHES_API' in template
        assert 'CONTENT_MATCHES_RUNTIME' in template
        assert (
            '(METADATA_MATCHES_API OR CONTENT_MATCHES_API) AND (METADATA_MATCHES_RUNTIME OR CONTENT_MATCHES_RUNTIME)'
        ) in template
        assert 'official API integration guidance' in template
        assert 'IMPLEMENTATION_LANGUAGE_RUNTIME' in template
        assert 'Technologies: {api_name} API, {IMPLEMENTATION_LANGUAGE_RUNTIME}' in template
        assert 'Topics: apidocs, apiintegration, official sdk, client library, http endpoints' in template
        assert 'Official API integration docs for {api_name} in {IMPLEMENTATION_LANGUAGE_RUNTIME}' in template
        assert 'SDK/client library vs direct HTTP based on official docs' in template
        assert 'AUTO_API_PROMPTS = []' in template
        assert 'SYNTHESIS_QUEUE = deduplicated list of normalized SYNTHESIZE_PROMPTS + AUTO_API_PROMPTS' in template
        assert 'PENDING_PROMPTS = copy(SYNTHESIS_QUEUE)' in template
        assert 'SYNTHESIZED_READ_BLOCKS = []' in template
        assert '- "  - Source: synthesized"' in template
        assert 'Covers API' in template
        assert 'covered by content-validated official .best-practices API docs' in template
        assert 'CANDIDATE_MARKER_PATHS' not in template
        assert 'read_path contains both `apidocs` and `apiintegration`' not in template
        assert 'lowercase slug marker topics apidocs apiintegration' not in template
        assert 'any EXISTING_BP_READ_PATHS item contains api_name OR API_SLUG_TOKEN' not in template

    def test_phase_template_completed_quality_loop_runs_synthesis_before_storage(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'IF LOOP_DECISION == "completed":' in template
        assert 'Proceed to Step 7.5.' in template

    def test_phase_template_uses_post_synthesis_critic_and_routes_api_blockers_to_loop(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'validation_mode: post_synthesis' in template
        assert '[API Research Final Docs Missing - BLOCKING]' in template
        assert 'POST_SYNTHESIS_DECISION_RESPONSE = ' in template
        assert 'Return to Step 5 (phase-architect will retrieve post-synthesis feedback from MCP itself)' in template
        assert 'Proceed to Step 8.' in template
        assert 'EXIT: Do NOT proceed to Step 8 with missing external API docs' not in template

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

    def test_plan_template_uses_feedback_memory_for_plan_and_analyst_refinement(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )

        assert 'PRIOR_CRITIC_FEEDBACK = CRITIC_FEEDBACK' in template
        assert 'previous_feedback_markdown' in template
        assert 'ANALYST_FEEDBACK = mcp__respec-ai__get_feedback' in template
        assert 'LATEST_FEEDBACK = mcp__respec-ai__get_feedback' in template

    def test_plan_template_fails_closed_when_analyst_artifacts_are_missing(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        assert 'ANALYST_ANALYSIS = ' in template
        assert 'Plan analyst did not confirm current-pass analysis storage' in template
        assert 'Plan analyst did not persist a retrievable analysis' in template
        assert 'No previous analysis found for loop' in template
        assert 'PRE_ANALYST_LOOP_STATUS = ' in template
        assert 'POST_ANALYST_LOOP_STATUS = ' in template
        assert 'ANALYST_FEEDBACK = ' in template
        assert 'Analyst critic did not persist CriticFeedback' in template
        assert 'Analyst critic did not advance loop state' in template
        assert 'Analyst critic did not persist fresh loop feedback' in template
        assert 'Do NOT call decide_loop_action' in template

    def test_plan_template_places_pre_loop_status_before_analyst_critic_invocation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PLAN, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        pre_loop_status_pos = template.find('PRE_ANALYST_LOOP_STATUS = ')
        invoke_critic_pos = template.find('Invoke the analyst-critic agent with loop ID:')

        assert pre_loop_status_pos != -1
        assert invoke_critic_pos != -1
        assert pre_loop_status_pos < invoke_critic_pos

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

    def test_code_template_fails_closed_before_decisions_and_commit_command(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'IF coder reports failure:' in template
        assert (
            'IF any invoked reviewer reports failure, returns no run summary, reports run_status=incomplete' in template
        )
        assert 'CONSOLIDATION_RESPONSE = ' in template
        assert 'Phase 1 review consolidation failed' in template
        assert 'PHASE1_FEEDBACK = ' in template
        assert 'Phase 1 consolidated feedback missing' in template
        assert 'Phase 2 review consolidation failed' in template
        assert 'STANDARDS_FEEDBACK = ' in template
        assert 'Phase 2 consolidated feedback missing' in template
        assert 'Do NOT invoke respec-commit' in template

    def test_task_template_passes_structured_reference_metadata(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'IMPL_PLAN_REFERENCES = []' in template
        assert 'Constraint Precedence Contract' in template
        assert 'TUI Plan Deviation Log' in template

    def test_task_template_fails_closed_when_task_or_feedback_is_missing(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Task planner did not confirm current-pass Task storage' in template
        assert 'TASK_MARKDOWN = ' in template
        assert 'Task planner did not produce a retrievable Task document' in template
        assert 'PRE_TASK_LOOP_STATUS = ' in template
        assert 'POST_TASK_LOOP_STATUS = ' in template
        assert 'TASK_FEEDBACK = ' in template
        assert 'Task plan critic did not persist CriticFeedback' in template
        assert 'Task plan critic did not advance loop state' in template
        assert 'Task plan critic did not persist fresh loop feedback' in template
        assert (
            'Return to Step 4.1 (task-planner → Task retrieval verification → task-plan-critic → feedback verification → decision)'
            in template
        )

    def test_task_template_places_pre_loop_status_before_task_plan_critic_invocation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        pre_loop_status_pos = template.find('PRE_TASK_LOOP_STATUS = ')
        invoke_critic_pos = template.find('Invoke the task-plan-critic workflow:')

        assert pre_loop_status_pos != -1
        assert invoke_critic_pos != -1
        assert pre_loop_status_pos < invoke_critic_pos

    def test_roadmap_template_fails_closed_when_roadmap_or_feedback_is_missing(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'Roadmap agent did not confirm current-pass roadmap storage' in template
        assert 'ROADMAP_MARKDOWN = ' in template
        assert 'Roadmap agent did not produce a retrievable roadmap' in template
        assert 'PRE_ROADMAP_LOOP_STATUS = ' in template
        assert 'POST_ROADMAP_LOOP_STATUS = ' in template
        assert 'ROADMAP_FEEDBACK = ' in template
        assert 'Roadmap critic did not persist CriticFeedback' in template
        assert 'Roadmap critic did not advance loop state' in template
        assert 'Roadmap critic did not persist fresh loop feedback' in template
        assert 'Override MCP decision and proceed to Step 5' not in template
        assert 'MCP will decide the next action after reevaluating stored feedback' in template

    def test_roadmap_template_places_pre_loop_status_before_roadmap_critic_invocation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        pre_loop_status_pos = template.find('PRE_ROADMAP_LOOP_STATUS = ')
        invoke_critic_pos = template.find('Invoke the roadmap-critic workflow with these instructions:')

        assert pre_loop_status_pos != -1
        assert invoke_critic_pos != -1
        assert pre_loop_status_pos < invoke_critic_pos

    def test_phase_template_fails_closed_on_main_and_post_synthesis_feedback_gaps(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        assert 'PRE_PHASE_LOOP_STATUS = ' in template
        assert 'POST_PHASE_LOOP_STATUS = ' in template
        assert 'PHASE_FEEDBACK = ' in template
        assert 'Phase critic did not persist CriticFeedback' in template
        assert 'Phase critic did not advance loop state' in template
        assert 'Phase critic did not persist fresh loop feedback' in template
        assert 'PRE_POST_SYNTHESIS_LOOP_STATUS = ' in template
        assert 'POST_POST_SYNTHESIS_LOOP_STATUS = ' in template
        assert 'POST_SYNTHESIS_FEEDBACK = ' in template
        assert 'Post-synthesis validation feedback missing' in template
        assert 'LATEST_POST_SYNTHESIS_SCORE = parse score from LATEST_POST_SYNTHESIS_FEEDBACK' in template
        assert 'Post-synthesis validation feedback preserved score 0' in template
        assert 'LATEST_POST_SYNTHESIS_SUMMARY != "Post-synthesis path validation"' in template
        assert 'Post-synthesis validation feedback summary mismatch' in template
        assert 'Post-synthesis phase critic did not advance loop state' in template
        assert 'Post-synthesis phase critic did not persist fresh loop feedback' in template
        assert 'validation_result contains' not in template

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
        assert 'ORCHESTRATOR BOUNDARY' in template
        assert 'This command is an orchestrator, not an implementation agent.' in template
        assert 'Do NOT directly edit source code.' in template
        assert 'Do NOT directly edit tests.' in template
        assert 'ALL source-code and test implementation MUST be delegated to `respec-coder`.' in template
        assert 'If `respec-coder` cannot be invoked, fail closed with diagnostics.' in template
        assert 'Run static analysis manually' not in template
        assert 'Continue with manual quality assessment' not in template
        assert 'single-pass workflow' not in template
        assert '# D) Phase 1 commit orchestration (every pass)' in template
        assert 'COMMIT_KIND = "phase1-checkpoint"' in template
        assert 'COMMIT_KIND = "phase2-checkpoint"' in template
        assert 'COMMIT_KIND = "final"' in template
        assert 'COMMIT_WORKFLOW_KIND = "code"' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'COMMIT_METADATA_MARKDOWN = compose markdown:' not in template
        assert 'git commit --' not in template
        assert 'COMMIT_MESSAGE_BLOCK' not in template
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
        assert 'PROJECT_CONFIG_CONTEXT_MARKDOWN = compose markdown:' in template
        assert '### Standards Guide Markdown' in template

    def test_code_template_phase1_loop_orders_commit_before_transitions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 7.4: Phase 1 Iteration Loop (Coder → Reviews → Decision → Commit)' in template
        assert '# D) Phase 1 commit orchestration (every pass)' in template
        assert '# E) Decision handling after commit' in template
        assert template.index('# D) Phase 1 commit orchestration (every pass)') < template.index(
            '# E) Decision handling after commit'
        )
        assert 'Return to Step 7.4 (next loop pass runs coder → reviews → decision → commit).' in template

    def test_code_template_reuses_signed_off_reviewers_with_full_roster_consolidation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'PHASE1_SIGNED_OFF_REVIEWERS = PHASE1_SIGNED_OFF_REVIEWERS if defined else []' in template
        assert 'PHASE1_REVIEWERS_TO_INVOKE = []' in template
        assert (
            'Set PHASE1_INVALIDATED_REVIEWERS by applying these rules to each reviewer in PHASE1_SIGNED_OFF_REVIEWERS'
        ) in template
        assert 'Add all Phase 1 reviewers when the Task document, Phase document' in template
        assert 'Rerun on uncertainty by adding the uncertain reviewer.' in template
        assert 'Launch only PHASE1_REVIEWERS_TO_INVOKE in parallel.' in template
        assert 'ACTIVE_REVIEWERS = PHASE1_REVIEWERS' in template
        assert 'returns no run summary, reports run_status=incomplete' in template
        assert 'Update PHASE1_SIGNED_OFF_REVIEWERS from the consolidated reviewer sections' in template
        assert 'STANDARDS_REVIEWER_SIGNED_OFF = STANDARDS_REVIEWER_SIGNED_OFF if defined else false' in template
        assert 'Reusing prior coding-standards-reviewer sign-off for this iteration' in template

    def test_code_template_phase1_commit_subject_is_checkpoint_only(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'COMMIT_KIND = "phase1-checkpoint"' in template
        assert 'COMMIT_WORKFLOW_KIND = "code"' in template
        assert 'COMMIT_SUBJECT = "feat: complete {PHASE_NAME}"' not in template
        assert 'ALLOW_EMPTY = true' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'Decision: {{CODING_DECISION}}\n    Score: {{PHASE1_SCORE}}/100' not in template

    def test_code_template_uses_mandatory_precommit_completion_gate(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'PRECOMMIT_EXIT_CODE = run: pre-commit run -a' in template
        assert 'Finalization is non-compliant until hooks pass.' in template
        assert 'Classify the failure from the hook transcript before branching.' in template
        assert 'COMPLETION_GATE_FAILURE_KIND = classify from hook transcript as exactly one of:' in template
        assert 'COMPLETION_GATE_STATUS = "deferred-external-blocker"' in template
        assert 'Proceeding to final completion commit with deferred external blocker' in template
        assert (
            'Use AskUserQuestion with options:' not in template[template.index('### 8.5 Completion Gate (Mandatory)') :]
        )
        assert 'Finalize now with deferred-risk summary (retry completion gate)' not in template
        assert 'COMMIT_KIND = "final"' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'Append in deterministic order: Test, Type check, Lint' not in template

    def test_code_template_separates_rubric_score_from_review_state(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Current rubric score and iteration' in template
        assert 'Functional Rubric Score' in template
        assert 'Rubric Score: {CODING_SCORE}/100' in template
        assert 'Rubric Score: {STANDARDS_SCORE}/100' in template
        assert 'threshold reached, no active blockers' not in template

    def test_codex_code_template_uses_command_owned_git_commit_rules(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert '$Commit' not in template
        assert 'Invoke the `respec-commit` skill with: `{COMMIT_KIND}`.' in template
        assert 'git commit --' not in template

    def test_commit_command_owns_standardized_commit_format_and_git_mechanics(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.COMMIT,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'allowed-tools: Bash' in template
        assert 'Task(' not in template
        assert 'Do NOT edit source files.' in template
        assert 'Do NOT edit test files.' in template
        assert 'Do NOT run pre-commit.' in template
        assert 'Do NOT retrieve MCP feedback.' in template
        assert 'Do NOT decide workflow branch outcomes.' in template
        assert 'COMMIT_KIND not in {phase1-checkpoint, phase2-checkpoint, final}' in template
        assert 'COMMIT_WORKFLOW_KIND not in {code, patch}' in template
        assert 'SUBJECT = "[WIP] patch {PHASE_NAME} [Phase 1 iter {CODING_ITERATION}]"' in template
        assert 'SUBJECT = "[WIP] {PHASE_NAME} [Phase 1 iter {CODING_ITERATION}]"' in template
        assert 'SUBJECT = "[WIP] patch {PHASE_NAME} [Phase 2 iter {STANDARDS_ITERATION}]"' in template
        assert 'SUBJECT = "[WIP] {PHASE_NAME} [Phase 2 iter {STANDARDS_ITERATION}]"' in template
        assert 'SUBJECT = "fix: complete {REQUEST_SUMMARY}"' in template
        assert 'SUBJECT = "feat: complete {PHASE_NAME}"' in template
        assert 'RUN git status --porcelain' in template
        assert 'RUN git add -A' in template
        assert "RUN git commit --allow-empty --no-verify -F - <<'EOF'" in template
        assert "RUN git commit --no-verify -F - <<'EOF'" in template
        assert "RUN git commit --amend --no-verify -F - <<'EOF'" in template
        assert 'Commit stored: hash={COMMIT_HASH}, kind={COMMIT_KIND}, workflow={COMMIT_WORKFLOW_KIND}' in template

    def test_codex_code_template_uses_direct_numbered_selection_instructions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'Present these options directly to the user in the chat UI as a numbered list.' in template
        assert 'This is a user-facing prompt, not an internal instruction.' in template
        assert 'WAIT for the user response.' in template
        assert 'DO NOT treat this as workflow completion, cancellation, or failure.' in template
        assert 'After the user responds, resume at Step 1.3.' in template
        assert 'After the user responds, resume at Step 6.7.' in template
        assert 'After the user responds, resume at Step 8.' in template
        assert 'After the user responds, resume at Step 7.5.' in template
        assert 'DO NOT explain that the workflow is stopping unless the user asks why.' in template
        assert 'Use AskUserQuestion' not in template
        assert 'Ask the user directly with a numbered options list' not in template
        assert 'mixed' not in template

    def test_opencode_code_template_uses_question_tool_selection_instructions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=OpenCodeAdapter(),
        )
        assert 'Use question tool to present options:' in template
        assert 'WAIT for question response.' in template
        assert 'Use AskUserQuestion' not in template
        assert 'Ask the user directly with a numbered options list' not in template
        assert 'mixed' not in template

    def test_code_template_accepts_optional_context_and_normalizes_it_for_shared_agents(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [plan-name] [phase request]' in template
        assert 'RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]' in template
        assert 'OPTIONAL_CONTEXT = [empty until RAW_PHASE_REQUEST is clarified]' in template
        assert 'Do NOT begin phase lookup until the phase reference is sufficiently clear.' in template
        assert 'WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:' in template
        assert 'workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN' in template
        assert 'project_config_context_markdown: PROJECT_CONFIG_CONTEXT_MARKDOWN' in template
        assert 'review_iteration: REVIEW_ITERATION' in template
        assert 'STANDARDS_REVIEW_ITERATION = 1' in template
        assert 'REVIEW_ITERATION = STANDARDS_REVIEW_ITERATION' in template
        assert 'phase2_mode: true' not in template

    def test_patch_template_uses_explicit_wait_resume_contract_for_all_user_input_branches(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'After the user responds, resume at Step 1.2. Set EXECUTION_MODE.' in template
        assert 'After the user responds, resume at Step 1.3. Clarify RAW_REQUEST.' in template
        assert 'After the user responds, resume at Step 2.3. Set PHASE_FILE_PATH.' in template
        assert 'After the user responds, resume at Step 3.6. Store the guidance with' in template
        assert 'After the user responds, resume at Step 4.1.1. Set EXECUTION_MODE.' in template
        assert 'After the user responds, resume at Step 6. Store the guidance with' in template
        assert 'After the user responds, resume at Step 6.5.' in template
        assert 'DO NOT explain that the workflow is stopping unless the user asks why.' in template

    def test_roadmap_template_uses_explicit_wait_resume_contract_for_guidance_and_user_input(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'resume at Step 0.1. Update PHASING_PREFERENCES. Continue to Step 0.2 immediately.' in template
        assert 'resume at Step 4. Branch on the selected option.' in template
        assert 'DO NOT explain that the workflow is stopping unless the user asks why.' in template

    def test_all_command_templates_use_imperative_language_in_actionable_sections(self) -> None:
        coordinator = TemplateCoordinator()
        adapters = (ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter())

        for adapter in adapters:
            for command in RespecAICommand:
                template = coordinator.generate_command_template(command, PlatformType.LINEAR, tui_adapter=adapter)
                _assert_no_soft_action_language(template, _COMMAND_ACTION_SECTION_TOKENS)

    def test_task_template_excludes_stale_create_task_target(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Task(respec-create-task)' not in template

    def test_task_template_accepts_optional_context_and_forwards_it(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [plan-name] [phase request]' in template
        assert 'RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]' in template
        assert 'OPTIONAL_CONTEXT = [empty until RAW_PHASE_REQUEST is clarified]' in template
        assert 'Do NOT begin phase lookup until the phase reference is sufficiently clear.' in template
        assert 'After the user responds, resume at Step 0.1.3.' in template
        assert 'After the user responds, resume at Step 5.' in template
        assert 'REFERENCE_CONTEXT_MARKDOWN = compose markdown:' in template
        assert 'WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:' in template
        assert 'reference_context_markdown: REFERENCE_CONTEXT_MARKDOWN' in template
        assert 'workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN' in template

    def test_phase_template_uses_raw_phase_request_contract(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [plan-name] [phase request]' in template
        assert 'RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]' in template
        assert 'OPTIONAL_INSTRUCTIONS = [empty until RAW_PHASE_REQUEST is clarified]' in template
        assert 'Do NOT begin phase lookup until the phase reference is sufficiently clear.' in template
        assert 'After the user responds, resume at Step 1.3.' in template

    def test_roadmap_template_uses_raw_guidance_contract(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [plan-name] [optional: roadmap-guidance]' in template
        assert 'RAW_PHASING_REQUEST = [all remaining input after PLAN_NAME]' in template
        assert (
            'PHASING_PREFERENCES = [normalized roadmap-guidance brief derived from RAW_PHASING_REQUEST, or empty string]'
            in template
        )
        assert 'WAIT for AskUserQuestion response.' in template
        assert 'DO NOT treat this as workflow completion, cancellation, or failure.' in template
        assert 'After the user responds, resume at Step 0.1.' in template
        assert 'After the user responds, resume at Step 4.' in template

    def test_patch_template_requires_upfront_mode_and_code_quality_core_reviewer(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 1.2: Capture Execution Mode (MANDATORY)' in template
        assert 'Header: "Patch Mode"' in template
        assert 'IF RAW_REQUEST already contains one unambiguous execution mode token:' in template
        assert 'EXECUTION_MODE_SOURCE = "raw-request"' in template
        assert 'EXECUTION_MODE = [selected option label normalized to MVP|hardening]' in template
        assert 'DO NOT treat this as workflow completion, cancellation, or failure.' in template
        assert 'After the user responds, resume at Step 1.2.' in template
        assert 'After the user responds, resume at Step 1.3.' in template
        assert 'After the user responds, resume at Step 2.3.' in template
        assert 'After the user responds, resume at Step 4.1.1.' in template
        assert 'After the user responds, resume at Step 6.5.' in template
        assert 'DO NOT explain that the workflow is stopping unless the user asks why.' in template
        assert '- mixed: Balance feature completion and targeted hardening' not in template
        assert 'mixed' not in template
        assert (
            'ACTIVE_REVIEWERS = ["automated-quality-checker", "spec-alignment-reviewer", "code-quality-reviewer"]'
            in template
        )
        assert 'Task(respec-code-quality-reviewer)' in template
        assert 'ORCHESTRATOR BOUNDARY' in template
        assert 'This command is an orchestrator, not an implementation agent.' in template
        assert 'Do NOT directly edit source code.' in template
        assert 'Do NOT directly edit tests.' in template
        assert 'ALL source-code and test implementation MUST be delegated to `respec-coder`.' in template
        assert 'If `respec-coder` cannot be invoked, fail closed with diagnostics.' in template
        assert 'Run static analysis manually' not in template
        assert 'Continue with manual quality assessment' not in template
        assert 'single-pass workflow' not in template

    def test_patch_template_includes_command_owned_commit_orchestration(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 5.3: Phase 1 Iteration Loop (Coder -> Reviews -> Decision -> Commit)' in template
        assert '# D) Phase 1 commit orchestration (every pass)' in template
        assert 'COMMIT_KIND = "phase1-checkpoint"' in template
        assert 'COMMIT_KIND = "phase2-checkpoint"' in template
        assert 'COMMIT_KIND = "final"' in template
        assert 'COMMIT_WORKFLOW_KIND = "patch"' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'COMMIT_METADATA_MARKDOWN = compose markdown:' not in template
        assert 'git commit --' not in template
        assert 'COMMIT_MESSAGE_BLOCK' not in template
        assert '#### Step 6.5.3: Exit to Completion Gate' in template
        assert '### 6.7 Completion Gate (Mandatory)' in template

    def test_patch_template_fails_closed_when_planner_or_critic_persistence_breaks(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )

        assert '#### Step 3.3: Invoke Patch Planner Agent and Verify Amendment Task Storage' in template
        assert 'PHASE_AMENDMENT_REQUIRED' in template
        assert 'Phase amendment required before patch coding' in template
        assert 'Do NOT retrieve TASK_MARKDOWN' in template
        assert 'run the Phase refinement workflow (`respec-phase`) before resuming patch work' in template
        assert 'TASK_MARKDOWN = ' in template
        assert 'Patch planner did not produce a retrievable amendment task' in template
        assert 'Do NOT invoke task-plan-critic' in template
        assert '#### Step 3.4: Invoke Task Plan Critic Agent and Verify Critic Persistence' in template
        assert 'PRE_PLANNING_LOOP_STATUS = ' in template
        assert 'POST_PLANNING_LOOP_STATUS = ' in template
        assert 'PLANNING_FEEDBACK = ' in template
        assert 'Task plan critic did not persist CriticFeedback' in template
        assert 'Task plan critic did not advance loop state' in template
        assert 'Task plan critic did not persist fresh loop feedback' in template
        assert 'Do NOT call decide_planning_action' in template
        assert 'Do NOT continue into code reconnaissance, implementation, or alternate storage paths' in template
        assert (
            'Do NOT use store_reviewer_result for task-plan-critic; it is a critic workflow and MUST persist via store_critic_feedback'
            in template
        )
        assert (
            'Return to Step 3.3 (planner → task retrieval verification → critic → critic persistence verification → decision).'
            in template
        )

    def test_patch_template_phase_evolution_log_update_is_append_only(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )

        assert '### 7. Append Phase Evolution Log Only' in template
        assert 'This is an append-only trace update.' in template
        assert 'Strip only the `## Evolution Log` section from PHASE_MARKDOWN and UPDATED_PHASE_MARKDOWN.' in template
        assert 'The stripped documents MUST match exactly byte-for-byte.' in template
        assert 'Research Requirements, Implementation Plan References, metadata, headings' in template
        assert 'Do NOT call update_phase_document' in template
        assert (
            'Direct user to run the Phase refinement workflow (`respec-phase`) for substantive Phase changes'
            in template
        )

    def test_patch_template_fails_closed_before_patch_loop_decisions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )

        assert 'IF coder reports failure:' in template
        assert (
            'IF any invoked reviewer reports failure, returns no run summary, reports run_status=incomplete' in template
        )
        assert 'CONSOLIDATION_RESPONSE = ' in template
        assert 'Phase 1 review consolidation failed' in template
        assert 'Phase 1 review consolidation iteration mismatch' in template
        assert 'Phase 1 consolidated feedback missing' in template
        assert 'Do NOT call decide_coding_action' in template
        assert 'Do NOT invoke respec-commit' in template
        assert 'IF invoked coding-standards-reviewer reports failure, returns no run summary,' in template
        assert 'Phase 2 review consolidation failed' in template
        assert 'Phase 2 review consolidation iteration mismatch' in template
        assert 'Phase 2 consolidated feedback missing' in template
        assert 'Do NOT call decide_standards_action' in template

    def test_patch_template_reuses_signed_off_reviewers_with_full_roster_consolidation(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )

        assert 'PHASE1_SIGNED_OFF_REVIEWERS = PHASE1_SIGNED_OFF_REVIEWERS if defined else []' in template
        assert 'PHASE1_REVIEWERS_TO_INVOKE = []' in template
        assert 'amendment-task context changes, patch scope changes' in template
        assert (
            'Set PHASE1_INVALIDATED_REVIEWERS by applying these rules to each reviewer in PHASE1_SIGNED_OFF_REVIEWERS'
        ) in template
        assert 'Add all Phase 1 reviewers when the Task document, Phase document' in template
        assert 'Rerun on uncertainty by adding the uncertain reviewer.' in template
        assert 'Launch only PHASE1_REVIEWERS_TO_INVOKE in parallel.' in template
        assert 'ACTIVE_REVIEWERS = PHASE1_REVIEWERS' in template
        assert 'returns no run summary, reports run_status=incomplete' in template
        assert 'Update PHASE1_SIGNED_OFF_REVIEWERS from the consolidated reviewer sections' in template
        assert 'STANDARDS_REVIEWER_SIGNED_OFF = STANDARDS_REVIEWER_SIGNED_OFF if defined else false' in template
        assert 'Reusing prior coding-standards-reviewer sign-off for this iteration' in template

    def test_phase_and_roadmap_templates_do_not_include_malformed_tool_calls(self) -> None:
        coordinator = TemplateCoordinator()
        roadmap_template = coordinator.generate_command_template(
            RespecAICommand.ROADMAP, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        phase_template = coordinator.generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )

        assert 'LOOP_DECISION_RESPONSE = {tools.decide_loop_action})' not in roadmap_template
        assert 'LOOP_DECISION_RESPONSE = {tools.decide_loop_action})' not in phase_template
        assert 'LOOP_STATUS = {tools.get_loop_status})' not in phase_template

    def test_patch_template_loads_optional_standards_guides_for_coder(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'GUIDE_FILES = Glob(.respec-ai/config/standards/guides/*.md)' in template
        assert 'PROJECT_CONFIG_CONTEXT_MARKDOWN = compose markdown:' in template
        assert '### Standards Guide Markdown' in template

    def test_patch_template_phase1_loop_orders_commit_before_transitions(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert '#### Step 5.3: Phase 1 Iteration Loop (Coder -> Reviews -> Decision -> Commit)' in template
        assert '# D) Phase 1 commit orchestration (every pass)' in template
        assert '# E) Decision handling after commit' in template
        assert template.index('# D) Phase 1 commit orchestration (every pass)') < template.index(
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
        assert 'COMMIT_KIND = "phase1-checkpoint"' in template
        assert 'COMMIT_WORKFLOW_KIND = "patch"' in template
        assert 'COMMIT_SUBJECT = "fix: complete {CHANGE_DESCRIPTION}"' not in template
        assert 'ALLOW_EMPTY = true' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'Decision: {{CODING_DECISION}}\n    Score: {{PHASE1_SCORE}}/100' not in template

    def test_patch_template_uses_mandatory_precommit_completion_gate(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'PRECOMMIT_EXIT_CODE = run: pre-commit run -a' in template
        assert 'Finalization is non-compliant until hooks pass.' in template
        assert 'Classify the failure from the hook transcript before branching.' in template
        assert 'COMPLETION_GATE_FAILURE_KIND = classify from hook transcript as exactly one of:' in template
        assert 'COMPLETION_GATE_STATUS = "deferred-external-blocker"' in template
        assert 'Proceeding to final completion commit with deferred external blocker' in template
        assert (
            'Use AskUserQuestion with options:' not in template[template.index('### 6.7 Completion Gate (Mandatory)') :]
        )
        assert 'Finalize now and retry completion gate' not in template
        assert 'COMMIT_KIND = "final"' in template
        assert '/respec-commit {COMMIT_KIND}' in template
        assert 'Append in deterministic order: Test, Type check, Lint' not in template

    def test_patch_template_separates_rubric_score_from_review_state(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Current rubric score and iteration' in template
        assert 'Functional Rubric Score' in template
        assert 'Rubric Score: {CODING_SCORE}/100' in template
        assert 'Rubric Score: {STANDARDS_SCORE}/100' in template
        assert 'threshold reached, no active blockers' not in template

    def test_patch_template_infers_context_from_single_request(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'argument-hint: [plan-name] [request]' in template
        assert 'argument-hint: [plan-name] [change-description] [optional: additional-context]' not in template
        assert '### 1. Parse User Inputs' in template
        assert 'RAW_REQUEST = [all remaining input after PLAN_NAME]' in template
        assert '#### Step 1.1: Initialize Workflow Variables' in template
        assert 'PATCH_REQUEST_BRIEF = [normalized request produced after clarification]' in template
        assert 'REQUEST_SUMMARY = [one-line summary produced from PATCH_REQUEST_BRIEF]' in template
        assert 'REQUEST_TEXT = [second argument from command - full patch request]' not in template
        assert 'CHANGE_DESCRIPTION = [explicit change inferred from REQUEST_TEXT]' not in template
        assert (
            'OPTIONAL_CONTEXT = [supporting context inferred from REQUEST_TEXT, otherwise empty string]' not in template
        )
        assert 'WORKFLOW_GUIDANCE_MARKDOWN = compose markdown from PATCH_REQUEST_BRIEF:' in template
        assert 'workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN' in template
        assert 'review_iteration: REVIEW_ITERATION' in template
        assert 'STANDARDS_REVIEW_ITERATION = 1' in template
        assert 'REVIEW_ITERATION = STANDARDS_REVIEW_ITERATION' in template
        assert 'phase2_mode: true' not in template
        assert 'raw_request: RAW_REQUEST' not in template
        assert 'Do NOT derive execution inputs from an ambiguous RAW_REQUEST.' in template
        assert 'Do NOT invoke the patch planner until the request is sufficiently clear.' in template

    def test_codex_patch_template_treats_missing_mode_as_resume_checkpoint(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'Present these options directly to the user in the chat UI as a numbered list.' in template
        assert 'This is a user-facing prompt, not an internal instruction.' in template
        assert 'WAIT for the user response.' in template
        assert 'DO NOT treat this as workflow completion, cancellation, or failure.' in template
        assert 'After the user responds, resume at Step 1.2.' in template
        assert 'DO NOT explain that the workflow is stopping unless the user asks why.' in template

    def test_codex_patch_template_uses_isolated_agent_handoff_wording(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PATCH,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'Use the rendered runtime agent name exactly.' in template
        assert 'Pass only the listed explicit inputs.' in template
        assert 'Do not rely on any unlisted conversation history or prior thread context.' in template
        assert 'Require the agent to retrieve any additional needed context through its own tools.' in template
        assert 'forked-context' not in template
        assert 'full-history' not in template
        assert 'parent context' not in template
        assert 'inherits' not in template

    def test_selection_prompt_contract_is_adapter_owned_across_interactive_commands(self) -> None:
        coordinator = TemplateCoordinator()
        codex_phrase = 'Present these options directly to the user in the chat UI as a numbered list.'
        claude_phrase = 'Use AskUserQuestion tool to present options:'
        opencode_phrase = 'Use question tool to present options:'

        for command in (
            RespecAICommand.PATCH,
            RespecAICommand.CODE,
            RespecAICommand.TASK,
            RespecAICommand.ROADMAP,
            RespecAICommand.PHASE,
        ):
            codex_template = coordinator.generate_command_template(
                command,
                PlatformType.LINEAR,
                tui_adapter=CodexAdapter(),
            )
            assert codex_phrase in codex_template
            assert 'Ask the user directly with a numbered options list' not in codex_template

            claude_template = coordinator.generate_command_template(
                command,
                PlatformType.LINEAR,
                tui_adapter=ClaudeCodeAdapter(),
            )
            assert claude_phrase in claude_template

            opencode_template = coordinator.generate_command_template(
                command,
                PlatformType.LINEAR,
                tui_adapter=OpenCodeAdapter(),
            )
            assert opencode_phrase in opencode_template
            assert 'Ask the user directly with a numbered options list' not in opencode_template

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
        assert '/respec-commit {COMMIT_KIND}' in code_template
        assert '/respec-commit {COMMIT_KIND}' in patch_template
        assert 'COMMIT_METADATA_MARKDOWN = compose markdown:' not in code_template
        assert 'COMMIT_METADATA_MARKDOWN = compose markdown:' not in patch_template

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
        assert 'If AVAILABLE_LANGUAGES has exactly one entry:' in template
        assert 'No target provided; auto-selected single available language: {TARGET}.' in template
        assert 'MUST call AskUserQuestion to select one language or "all".' in template
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

    def test_standards_command_template_requires_explicit_target_when_prompt_tool_unsupported(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.STANDARDS,
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        assert 'argument-hint: [language|all]' in template
        assert 'AskUserQuestion' not in template
        assert 'If AVAILABLE_LANGUAGES has exactly one entry:' in template
        assert 'No target provided; auto-selected single available language: {TARGET}.' in template
        assert 'standards_target_required: explicit target required on this TUI.' in template
        assert 'Present numbered options for selection:' in template
        assert '1..N) one entry per AVAILABLE_LANGUAGES item (in deterministic sorted order)' in template
        assert 'N+1) all' in template
        assert '- respec-standards <language>' in template
        assert '- respec-standards all' in template

    def test_task_command_persists_actual_task_identity_from_final_task_document(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.TASK,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'Parse FINAL_TASK as Task markdown.' in template
        assert 'TASK_NAME = [extract the H1 title value after "# Task:" from FINAL_TASK]' in template
        assert 'PHASE_NAME.replace("phase-", "task-", 1)' not in template

    def test_phase_command_verifies_actual_created_task_identity(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.PHASE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'mcp__respec-ai__list_documents(' in template
        assert 'TASK_DOC_KEY = [extract the single returned task document key from TASK_RESULT]' in template
        assert 'TASK_NAME = PHASE_NAME.replace("phase-", "task-", 1)' not in template

    def test_code_command_requires_explicit_task_selection_for_multi_task_phase(self) -> None:
        coordinator = TemplateCoordinator()
        template = coordinator.generate_command_template(
            RespecAICommand.CODE,
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert template.count('Resolve Concrete Task Identity and Link Task Retrieval Loop') == 1
        assert 'mcp__respec-ai__list_documents(doc_type="task", parent_key={PLAN_NAME}/{PHASE_NAME})' in template
        assert (
            "Multiple Task documents exist for phase '{PHASE_NAME}'. Select the task for this coding loop." in template
        )
        assert (
            'TASK_LOOP_ID = mcp__respec-ai__initialize_refinement_loop(plan_name={PLAN_NAME}, loop_type="task")'
            in template
        )
        assert (
            'mcp__respec-ai__link_loop_to_document(loop_id={TASK_LOOP_ID}, doc_type="task", key={TASK_DOC_KEY})'
            in template
        )
        assert 'use plan_name/phase_name to find active task loop' not in template
        assert 'Retrieve Task from respec-task Command' not in template

        task_selection_index = template.index('### 5. Resolve Concrete Task Identity and Link Task Retrieval Loop')
        override_index = template.index('### 6. Check for Architectural Override Proposals')
        step_modes_index = template.index('### 6.5 Extract Step Modes from Task')
        policy_index = template.index('### 6.7 Resolve Delivery Intent Policy')
        assert task_selection_index < override_index < step_modes_index < policy_index
