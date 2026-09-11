"""Behavior tests for nested-subagent orchestration capability tiering."""

from pathlib import Path

from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import (
    AGENT_CAPABILITY_REQUIREMENTS,
    _agents_for_adapter,
    expected_agents_count,
    expected_commands_count,
    generate_templates,
)
from src.platform.models.roadmap import PlanRoadmapCommandTools
from src.platform.template_helpers import THIN_ROADMAP_COMMAND_TOOLS
from src.platform.tool_enums import BuiltInToolCapability, RespecAITool
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter


def _opencode_adapter() -> OpenCodeAdapter:
    return OpenCodeAdapter(model_overrides={'orchestration': 'test-model', 'reasoning': 'test-model'})


def _codex_adapter() -> CodexAdapter:
    return CodexAdapter(model_overrides={'orchestration': 'test-model', 'reasoning': 'test-model'})


def _all_adapters() -> tuple[tuple[str, TuiAdapter], ...]:
    return (
        ('claude', ClaudeCodeAdapter()),
        ('opencode', _opencode_adapter()),
        ('codex', _codex_adapter()),
    )


class TestNestedTaskCapabilityDeclaration:
    def test_claude_code_declares_nested_task_support(self) -> None:
        assert ClaudeCodeAdapter().render_builtin_tool_name(BuiltInToolCapability.NESTED_TASK) == 'Task'

    def test_opencode_declares_no_nested_task_support(self) -> None:
        assert _opencode_adapter().render_builtin_tool_name(BuiltInToolCapability.NESTED_TASK) is None

    def test_codex_declares_no_nested_task_support(self) -> None:
        assert _codex_adapter().render_builtin_tool_name(BuiltInToolCapability.NESTED_TASK) is None


class TestAgentCapabilityTiering:
    def test_unrequired_agents_are_generated_for_every_adapter(self) -> None:
        for _label, adapter in _all_adapters():
            names = _agents_for_adapter(adapter)
            assert 'respec-roadmap' in names
            assert 'respec-roadmap-critic' in names

    def test_agents_requiring_an_undeclared_capability_are_filtered_out(self) -> None:
        AGENT_CAPABILITY_REQUIREMENTS['respec-test-only-agent'] = BuiltInToolCapability.NESTED_TASK
        try:
            assert 'respec-test-only-agent' not in _agents_for_adapter(_codex_adapter())
            assert 'respec-test-only-agent' not in _agents_for_adapter(_opencode_adapter())
        finally:
            del AGENT_CAPABILITY_REQUIREMENTS['respec-test-only-agent']

    def test_expected_agents_count_is_adapter_derived(self) -> None:
        for _label, adapter in _all_adapters():
            assert expected_agents_count(adapter) == len(_agents_for_adapter(adapter))


class TestWorkflowHandoffRendering:
    _PARAMS = [('plan_name', 'PLAN_NAME'), ('roadmap_loop_id', 'ROADMAP_LOOP_ID')]

    def _handoff(self, adapter: TuiAdapter) -> str:
        return adapter.render_workflow_handoff(
            'respec-roadmap',
            'respec-roadmap-orchestrator',
            'drive the roadmap quality loop',
            self._PARAMS,
            '{PLAN_NAME}',
        )

    def test_claude_code_dispatches_the_orchestrator_agent(self) -> None:
        handoff = self._handoff(ClaudeCodeAdapter())

        assert 'respec-roadmap-orchestrator' in handoff
        assert '/respec-roadmap' not in handoff

    def test_other_adapters_keep_the_portable_command_handoff(self) -> None:
        for adapter in (_opencode_adapter(), _codex_adapter()):
            handoff = self._handoff(adapter)

            assert 'respec-roadmap-orchestrator' not in handoff
            assert 'respec-roadmap' in handoff

    def test_portable_default_matches_plain_command_invocation(self) -> None:
        for adapter in (_opencode_adapter(), _codex_adapter()):
            assert self._handoff(adapter) == adapter.render_command_invocation(
                'respec-roadmap', '{PLAN_NAME}', '', False
            )


class TestSkillInvocationBlocking:
    _BLOCKED = ('respec-plan', 'respec-phase', 'respec-code', 'respec-patch', 'respec-roadmap')
    _INVOCABLE = ('respec-commit', 'respec-plan-conversation', 'respec-standards', 'respec-design-sync')

    def _claude_commands(self, tmp_path: Path) -> dict[str, str]:
        orchestrator = PlatformOrchestrator(str(tmp_path / 'cfg'))
        generate_templates(orchestrator, tmp_path, PlatformType.MARKDOWN, tui_adapter=ClaudeCodeAdapter())
        commands_dir = tmp_path / '.claude' / 'commands'
        return {path.stem: path.read_text(encoding='utf-8') for path in commands_dir.glob('*.md')}

    def test_entry_workflows_are_not_model_invocable(self, tmp_path: Path) -> None:
        commands = self._claude_commands(tmp_path)

        for name in self._BLOCKED:
            assert 'disable-model-invocation: true' in commands[name], name

    def test_chained_sub_workflows_stay_model_invocable(self, tmp_path: Path) -> None:
        # These stay reachable through Skill because respec-plan hands off to them by
        # rendered command text, which the main agent has no other way to act on. Skill
        # expansion strips allowed-tools, so each one is safe only because it carries no
        # orchestration: respec-plan-conversation is a pure conversation guarded by its
        # NO-SIDE-EFFECTS protocol, and the rest hold no agent-dispatch or loop tools.
        commands = self._claude_commands(tmp_path)

        for name in self._INVOCABLE:
            assert 'disable-model-invocation' not in commands[name], name

    def test_other_tuis_never_emit_the_claude_only_frontmatter_key(self, tmp_path: Path) -> None:
        for label, adapter in (('opencode', _opencode_adapter()), ('codex', _codex_adapter())):
            project_path = tmp_path / label
            orchestrator = PlatformOrchestrator(str(tmp_path / f'{label}-cfg'))
            generate_templates(orchestrator, project_path, PlatformType.MARKDOWN, tui_adapter=adapter)

            for path in project_path.rglob('*'):
                if path.is_file():
                    assert 'disable-model-invocation' not in path.read_text(encoding='utf-8'), path


class TestThinRoadmapCommandGrant:
    def test_thin_grant_is_a_subset_of_the_portable_superset(self) -> None:
        # The ClassVar stays the portable superset; the thin command selects from it.
        # A tool added to the ClassVar alone silently never reaches the thin command.
        assert set(THIN_ROADMAP_COMMAND_TOOLS).issubset(set(PlanRoadmapCommandTools.respec_ai_tools))

    def test_thin_grant_holds_no_loop_management_tools(self) -> None:
        for tool in (
            RespecAITool.INITIALIZE_REFINEMENT_LOOP,
            RespecAITool.DECIDE_LOOP_NEXT_ACTION,
            RespecAITool.GET_LOOP_STATUS,
        ):
            assert tool not in THIN_ROADMAP_COMMAND_TOOLS, tool


class TestRoadmapGateLoopBindings:
    def _plan_command(self, tmp_path: Path) -> str:
        orchestrator = PlatformOrchestrator(str(tmp_path / 'cfg'))
        generate_templates(orchestrator, tmp_path, PlatformType.MARKDOWN, tui_adapter=ClaudeCodeAdapter())
        return (tmp_path / '.claude' / 'commands' / 'respec-plan.md').read_text(encoding='utf-8')

    def test_gate_reads_and_writes_the_roadmap_loop_not_the_analyst_or_plan_loop(self, tmp_path: Path) -> None:
        body = self._plan_command(tmp_path)
        gate = body.split('status: needs_user_input')[1].split('\nELSE:\n')[0]

        assert 'get_feedback(loop_id={ROADMAP_LOOP_ID}' in gate
        assert 'store_user_feedback(loop_id={ROADMAP_LOOP_ID}' in gate
        assert 'ANALYST_LOOP_ID' not in gate
        assert 'PLAN_LOOP_ID' not in gate

    def test_handoff_variables_are_initialized_before_first_dispatch(self, tmp_path: Path) -> None:
        body = self._plan_command(tmp_path)
        setup = body.split('## Step 1.5')[0]

        assert '`ROADMAP_LOOP_ID = None`' in setup
        assert '`PHASING_PREFERENCES = ""`' in setup


class TestGeneratedCountsAgreeAcrossTuis:
    def test_regenerate_succeeds_for_all_three_tuis(self, tmp_path: Path) -> None:
        for label, adapter in _all_adapters():
            orchestrator = PlatformOrchestrator(str(tmp_path / f'{label}-config'))
            _files, commands_count, agents_count = generate_templates(
                orchestrator, tmp_path / label, PlatformType.MARKDOWN, tui_adapter=adapter
            )
            assert commands_count == expected_commands_count(adapter)
            assert agents_count == expected_agents_count(adapter)

    def test_validate_style_counts_agree_with_generated_files_for_every_tui(self, tmp_path: Path) -> None:
        for label, adapter in _all_adapters():
            project_path = tmp_path / label
            orchestrator = PlatformOrchestrator(str(tmp_path / f'{label}-config'))
            generate_templates(orchestrator, project_path, PlatformType.MARKDOWN, tui_adapter=adapter)

            assert adapter.count_generated_commands(project_path) == expected_commands_count(adapter)
            assert adapter.count_generated_agents(project_path) == expected_agents_count(adapter)
