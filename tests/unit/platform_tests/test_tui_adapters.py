import json
import inspect
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, get_tui_adapter
from src.platform.tui_adapters.base import AgentSpec, CommandSpec
from src.platform.tui_adapters import codex as codex_adapter_module
from src.platform.tui_adapters.opencode import OpenCodeAdapter
from src.platform.tui_adapters import opencode as opencode_adapter_module
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.platform_selector import PlatformType
from src.platform.tool_enums import BuiltInToolCapability, RespecAICommand
from src.platform.tui_selector import TuiType


@pytest.fixture
def project_path() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def agent_spec() -> AgentSpec:
    return AgentSpec(
        name='respec-plan-analyst',
        description='Extract structured objectives from strategic plans',
        model='sonnet',
        tools=['Task(respec-plan-critic)', 'mcp__respec-ai__get_plan', 'Read'],
        body='# respec-plan-analyst\n\nYou are a business analyst.',
        color='blue',
        is_orchestrator=False,
    )


@pytest.fixture
def command_spec() -> CommandSpec:
    return CommandSpec(
        name='respec-plan',
        description='Orchestrate strategic planning workflow',
        argument_hint='[plan-name]',
        tools=['Task(respec-plan-analyst)', 'Task(respec-plan-critic)', 'mcp__respec-ai__save_plan'],
        body='# Strategic Planning\n\nRun the planning workflow.',
        delegated_agents=['respec-plan-analyst', 'respec-plan-critic'],
    )


class TestTuiType:
    def test_values(self) -> None:
        assert TuiType.CLAUDE_CODE == 'claude-code'
        assert TuiType.OPENCODE == 'opencode'
        assert TuiType.CODEX == 'codex'

    def test_from_string(self) -> None:
        assert TuiType('claude-code') == TuiType.CLAUDE_CODE
        assert TuiType('opencode') == TuiType.OPENCODE
        assert TuiType('codex') == TuiType.CODEX


class TestGetTuiAdapter:
    def test_returns_claude_code_adapter(self) -> None:
        adapter = get_tui_adapter(TuiType.CLAUDE_CODE)
        assert isinstance(adapter, ClaudeCodeAdapter)

    def test_returns_opencode_adapter(self) -> None:
        adapter = get_tui_adapter(TuiType.OPENCODE)
        assert isinstance(adapter, OpenCodeAdapter)

    def test_returns_codex_adapter(self) -> None:
        adapter = get_tui_adapter(TuiType.CODEX)
        assert isinstance(adapter, CodexAdapter)

    def test_invalid_tui_raises(self) -> None:
        with pytest.raises((ValueError, AttributeError)):
            get_tui_adapter('invalid')  # type: ignore[arg-type]

    def test_adapter_modules_do_not_import_cli_commands(self) -> None:
        codex_source = inspect.getsource(codex_adapter_module)
        opencode_source = inspect.getsource(opencode_adapter_module)

        assert 'from src.cli.commands import' not in codex_source
        assert 'from src.cli.commands import' not in opencode_source

    def test_all_adapters_define_runtime_decision_for_every_builtin_capability(self) -> None:
        expected = set(BuiltInToolCapability)

        for adapter in (ClaudeCodeAdapter(), OpenCodeAdapter(), CodexAdapter()):
            assert set(adapter.builtin_tool_name_map.keys()) == expected


class TestClaudeCodeAdapter:
    def setup_method(self) -> None:
        self.adapter = ClaudeCodeAdapter()

    def test_commands_dir(self, project_path: Path) -> None:
        assert self.adapter.commands_dir(project_path) == project_path / '.claude' / 'commands'

    def test_prompts_dir(self, project_path: Path) -> None:
        assert self.adapter.prompts_dir(project_path) == project_path / '.claude' / 'agents'

    def test_config_dir_name(self) -> None:
        assert self.adapter.config_dir_name() == '.claude'

    def test_no_adapter_level_commit_instruction_api(self) -> None:
        assert not hasattr(self.adapter, 'loop_commit_instructions')

    def test_reasoning_model(self) -> None:
        assert self.adapter.reasoning_model == 'opus'

    def test_task_model(self) -> None:
        assert self.adapter.task_model == 'sonnet'

    def test_selection_prompt_contract_uses_ask_user_question(self) -> None:
        assert self.adapter.selection_prompt_instruction == 'Use AskUserQuestion tool to present options:'
        assert self.adapter.selection_response_source == 'AskUserQuestion response'

    def test_render_agent_frontmatter(self, agent_spec: AgentSpec) -> None:
        result = self.adapter.render_agent(agent_spec)
        assert result.startswith('---\n')
        assert 'name: respec-plan-analyst' in result
        assert 'description: Extract structured objectives from strategic plans' in result
        assert 'model: sonnet' in result
        assert 'color: blue' in result
        assert 'tools: Task(respec-plan-critic), mcp__respec-ai__get_plan, Read' in result
        assert '---' in result

    def test_render_agent_includes_body(self, agent_spec: AgentSpec) -> None:
        result = self.adapter.render_agent(agent_spec)
        assert 'You are a business analyst.' in result

    def test_render_agent_no_color_when_none(self) -> None:
        spec = AgentSpec(
            name='test-agent',
            description='Test',
            model='sonnet',
            tools=['Read'],
            body='body',
            color=None,
            is_orchestrator=False,
        )
        result = self.adapter.render_agent(spec)
        assert 'color:' not in result

    def test_render_command_frontmatter(self, command_spec: CommandSpec) -> None:
        result = self.adapter.render_command(command_spec)
        assert result.startswith('---\n')
        assert 'allowed-tools:' in result
        assert 'argument-hint: [plan-name]' in result
        assert 'description: Orchestrate strategic planning workflow' in result

    def test_render_command_includes_body(self, command_spec: CommandSpec) -> None:
        result = self.adapter.render_command(command_spec)
        assert 'Run the planning workflow.' in result

    def test_write_all_creates_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        files = self.adapter.write_all(project_path, [agent_spec], [command_spec])

        assert len(files) == 2
        agent_file = project_path / '.claude' / 'agents' / 'respec-plan-analyst.md'
        command_file = project_path / '.claude' / 'commands' / 'respec-plan.md'
        assert agent_file.exists()
        assert command_file.exists()

    def test_write_all_cleans_stale_respec_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        agents_dir = project_path / '.claude' / 'agents'
        agents_dir.mkdir(parents=True)
        stale = agents_dir / 'respec-old-agent.md'
        stale.write_text('old content')

        self.adapter.write_all(project_path, [agent_spec], [command_spec])

        assert not stale.exists()

    def test_write_all_returns_paths(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        files = self.adapter.write_all(project_path, [agent_spec], [command_spec])
        assert all(isinstance(f, Path) for f in files)

    def test_write_all_agent_content(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        content = (project_path / '.claude' / 'agents' / 'respec-plan-analyst.md').read_text()
        assert 'name: respec-plan-analyst' in content
        assert 'You are a business analyst.' in content


class TestOpenCodeAdapter:
    def setup_method(self) -> None:
        self.adapter = OpenCodeAdapter()

    def test_commands_dir(self, project_path: Path) -> None:
        assert self.adapter.commands_dir(project_path) == project_path / '.opencode' / 'commands'

    def test_prompts_dir(self, project_path: Path) -> None:
        assert self.adapter.prompts_dir(project_path) == project_path / '.opencode' / 'prompts'

    def test_config_dir_name(self) -> None:
        assert self.adapter.config_dir_name() == '.opencode'

    def test_no_adapter_level_commit_instruction_api(self) -> None:
        assert not hasattr(self.adapter, 'loop_commit_instructions')

    def test_selection_prompt_contract_uses_question_tool(self) -> None:
        assert self.adapter.ask_user_question_tool_name == 'question'
        assert self.adapter.selection_prompt_instruction == 'Use question tool to present options:'
        assert self.adapter.selection_response_source == 'question response'

    def test_reasoning_model_returns_configured_value(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(
            json.dumps({'opencode': {'reasoning': 'opencode-go/kimi-k2.5', 'task': 'opencode-go/minimax-m2.7'}}),
            encoding='utf-8',
        )
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            assert self.adapter.reasoning_model == 'opencode-go/kimi-k2.5'

    def test_task_model_returns_configured_value(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(
            json.dumps({'opencode': {'reasoning': 'opencode-go/kimi-k2.5', 'task': 'opencode-go/minimax-m2.7'}}),
            encoding='utf-8',
        )
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            assert self.adapter.task_model == 'opencode-go/minimax-m2.7'

    def test_reasoning_model_raises_when_not_configured(self, tmp_path: Path) -> None:
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'missing.json'):
            with pytest.raises(RuntimeError, match='models opencode'):
                _ = self.adapter.reasoning_model

    def test_task_model_raises_when_not_configured(self, tmp_path: Path) -> None:
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'missing.json'):
            with pytest.raises(RuntimeError, match='models opencode'):
                _ = self.adapter.task_model

    def test_render_agent_returns_body(self, agent_spec: AgentSpec) -> None:
        result = self.adapter.render_agent(agent_spec)
        assert result == agent_spec.body
        assert '---' not in result

    def test_render_command_returns_body(self, command_spec: CommandSpec) -> None:
        result = self.adapter.render_command(command_spec)
        assert result == command_spec.body
        assert '---' not in result

    def test_write_all_creates_prompt_files_in_subdirectories(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])

        agent_file = project_path / '.opencode' / 'prompts' / 'agents' / 'respec-plan-analyst.md'
        command_file = project_path / '.opencode' / 'prompts' / 'commands' / 'respec-plan.md'
        assert agent_file.exists()
        assert command_file.exists()

    def test_write_all_creates_opencode_json(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        assert (project_path / 'opencode.json').exists()

    def test_opencode_json_has_schema(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['$schema'] == 'https://opencode.ai/config.json'

    def test_opencode_json_agent_mode_subagent(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['agent']['respec-plan-analyst']['mode'] == 'subagent'

    def test_opencode_json_agent_mode_primary_for_orchestrator(
        self, project_path: Path, command_spec: CommandSpec
    ) -> None:
        orchestrator = AgentSpec(
            name='respec-orchestrator',
            description='Test',
            model='sonnet',
            tools=['Read'],
            body='body',
            color=None,
            is_orchestrator=True,
        )
        self.adapter.write_all(project_path, [orchestrator], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['agent']['respec-orchestrator']['mode'] == 'primary'

    def test_opencode_json_command_agent_mode_primary(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['agent']['cmd-respec-plan']['mode'] == 'primary'

    def test_opencode_json_command_entry(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert 'respec-plan' in config['command']
        assert config['command']['respec-plan']['agent'] == 'cmd-respec-plan'

    def test_opencode_json_prompt_file_reference(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        prompt = config['agent']['respec-plan-analyst']['prompt']
        assert 'agents/respec-plan-analyst.md' in prompt

    def test_opencode_json_model_is_spec_model(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['agent']['respec-plan-analyst']['model'] == agent_spec.model

    def test_opencode_json_command_model_is_spec_model(self, project_path: Path, agent_spec: AgentSpec) -> None:
        cmd_spec = CommandSpec(
            name='respec-plan',
            description='Orchestrate strategic planning workflow',
            argument_hint='[plan-name]',
            tools=['Task(respec-plan-analyst)'],
            body='# Plan',
            delegated_agents=['respec-plan-analyst'],
            model='provider/custom-model',
        )
        self.adapter.write_all(project_path, [agent_spec], [cmd_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert config['agent']['cmd-respec-plan']['model'] == 'provider/custom-model'

    def test_opencode_json_builtin_tools_mapped(self, project_path: Path, command_spec: CommandSpec) -> None:
        spec = AgentSpec(
            name='respec-coder',
            description='Coder',
            model='sonnet',
            tools=['read', 'write', 'bash', 'question', 'mcp__respec-ai__get_plan'],
            body='body',
            color=None,
            is_orchestrator=False,
        )
        self.adapter.write_all(project_path, [spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        tools = config['agent']['respec-coder'].get('tools', {})
        assert tools.get('read') is True
        assert tools.get('write') is True
        assert tools.get('bash') is True
        assert tools.get('question') is True

    def test_opencode_json_task_permissions_on_command(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        plan_agent = config['agent']['cmd-respec-plan']
        assert 'permission' in plan_agent
        task_perms = plan_agent['permission']['task']
        assert task_perms.get('*') == 'deny'
        assert task_perms.get('respec-plan-analyst') == 'allow'
        assert task_perms.get('respec-plan-critic') == 'allow'

    def test_write_all_cleans_stale_prompt_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        prompts_dir = project_path / '.opencode' / 'prompts'
        agents_dir = prompts_dir / 'agents'
        agents_dir.mkdir(parents=True)
        stale = agents_dir / 'respec-old-agent.md'
        stale.write_text('old')

        self.adapter.write_all(project_path, [agent_spec], [command_spec])

        assert not stale.exists()

    def test_write_all_returns_paths(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        files = self.adapter.write_all(project_path, [agent_spec], [command_spec])
        assert all(isinstance(f, Path) for f in files)
        assert any(f.name == 'opencode.json' for f in files)

    def test_register_mcp_server_creates_entry(self, project_path: Path) -> None:
        result = self.adapter.register_mcp_server(project_path)
        assert result is True
        config = json.loads((project_path / 'opencode.json').read_text())
        assert 'respec-ai' in config['mcp']
        assert config['mcp']['respec-ai']['enabled'] is True

    def test_is_mcp_registered_false_when_no_file(self, project_path: Path) -> None:
        assert not self.adapter.is_mcp_registered(project_path)

    def test_is_mcp_registered_true_after_register(self, project_path: Path) -> None:
        self.adapter.register_mcp_server(project_path)
        assert self.adapter.is_mcp_registered(project_path)

    def test_add_mcp_permissions_noop(self, project_path: Path) -> None:
        assert self.adapter.add_mcp_permissions(project_path) is True

    def test_unregister_mcp_server_removes_entry(self, project_path: Path) -> None:
        self.adapter.register_mcp_server(project_path)
        assert self.adapter.is_mcp_registered(project_path)
        result = self.adapter.unregister_mcp_server(project_path)
        assert result is True
        assert not self.adapter.is_mcp_registered(project_path)

    def test_unregister_mcp_server_returns_false_when_not_registered(self, project_path: Path) -> None:
        assert self.adapter.unregister_mcp_server(project_path) is False

    def test_unregister_mcp_server_returns_false_no_file(self, project_path: Path) -> None:
        assert self.adapter.unregister_mcp_server(project_path) is False

    def test_unregister_mcp_server_preserves_other_config(self, project_path: Path) -> None:
        self.adapter.register_mcp_server(project_path)
        opencode_json = project_path / 'opencode.json'
        config = json.loads(opencode_json.read_text())
        config['mcp']['other-server'] = {'type': 'local', 'enabled': True}
        opencode_json.write_text(json.dumps(config))

        self.adapter.unregister_mcp_server(project_path)

        config = json.loads(opencode_json.read_text())
        assert 'respec-ai' not in config['mcp']
        assert 'other-server' in config['mcp']


class TestClaudeCodeAdapterInvocationRendering:
    def setup_method(self) -> None:
        self.adapter = ClaudeCodeAdapter()

    def test_render_agent_invocation_single_param(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-plan-critic',
            'evaluate strategic plan quality',
            [('plan_name', 'PLAN_NAME')],
        )
        assert 'Invoke: respec-plan-critic' in result
        assert '  - plan_name: PLAN_NAME' in result

    def test_render_agent_invocation_multiple_params(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-phase-architect',
            'design phase architecture',
            [('loop_id', 'LOOP_ID'), ('plan_name', 'PLAN_NAME'), ('phase_name', 'PHASE_NAME')],
        )
        assert 'Invoke: respec-phase-architect' in result
        assert 'Input:' in result
        assert '  - loop_id: LOOP_ID' in result
        assert '  - plan_name: PLAN_NAME' in result
        assert '  - phase_name: PHASE_NAME' in result

    def test_render_agent_invocation_no_params(self) -> None:
        result = self.adapter.render_agent_invocation('respec-plan-analyst', 'analyze plan', [])
        assert 'Invoke: respec-plan-analyst' in result
        assert 'Input:' not in result

    def test_render_command_invocation_interactive(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-plan-conversation',
            '[CONVERSATION_INITIAL_CONTEXT]',
            'inline guide text',
            requires_user_interaction=True,
        )
        assert result == '/respec-plan-conversation [CONVERSATION_INITIAL_CONTEXT]'

    def test_render_command_invocation_non_interactive(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-task',
            '{PLAN_NAME} {PHASE_NAME}',
            '',
            requires_user_interaction=False,
        )
        assert result == '/respec-task {PLAN_NAME} {PHASE_NAME}'

    def test_render_command_reference(self) -> None:
        assert self.adapter.render_command_reference('respec-phase') == '/respec-phase'

    def test_render_command_invocation_ignores_inline_guide(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-plan-conversation',
            '[ARGS]',
            'This guide should be ignored on Claude Code',
            requires_user_interaction=True,
        )
        assert 'This guide should be ignored' not in result
        assert result.startswith('/')


class TestOpenCodeAdapterInvocationRendering:
    def setup_method(self) -> None:
        self.adapter = OpenCodeAdapter()

    def test_render_agent_invocation_uses_task_call_syntax(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-plan-critic',
            'evaluate strategic plan quality',
            [('plan_name', 'PLAN_NAME')],
        )
        assert 'CALL task:' in result
        assert 'subagent_type: "respec-plan-critic"' in result
        assert 'prompt: |' in result

    def test_render_agent_invocation_includes_description(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-plan-critic',
            'evaluate strategic plan quality',
            [],
        )
        assert 'evaluate strategic plan quality.' in result

    def test_render_agent_invocation_embeds_params_in_prompt(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-phase-architect',
            'design phase architecture',
            [('loop_id', 'LOOP_ID'), ('plan_name', 'PLAN_NAME'), ('phase_name', 'PHASE_NAME')],
        )
        assert '    Parameters:' in result
        assert '    - loop_id: LOOP_ID' in result
        assert '    - plan_name: PLAN_NAME' in result
        assert '    - phase_name: PHASE_NAME' in result

    def test_render_agent_invocation_ends_with_wait(self) -> None:
        result = self.adapter.render_agent_invocation('respec-plan-critic', 'desc', [])
        assert result.endswith('Wait for agent completion before proceeding.')

    def test_render_agent_invocation_dynamic_reviewer_placeholder(self) -> None:
        result = self.adapter.render_agent_invocation(
            '{{REVIEWER}}',
            'perform domain-specific code review',
            [('coding_loop_id', '{{CODING_LOOP_ID}}')],
        )
        assert 'subagent_type: "{{REVIEWER}}"' in result
        assert '{{CODING_LOOP_ID}}' in result

    def test_render_command_invocation_interactive_returns_inline_guide(self) -> None:
        guide = 'Conduct conversational requirements gathering directly.'
        result = self.adapter.render_command_invocation(
            'respec-plan-conversation',
            '[ARGS]',
            guide,
            requires_user_interaction=True,
        )
        assert result == guide

    def test_render_command_invocation_non_interactive_returns_suggestion(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-task',
            '{PLAN_NAME} {PHASE_NAME}',
            '',
            requires_user_interaction=False,
        )
        assert '/respec-task' in result
        assert '{PLAN_NAME}' in result
        assert '{PHASE_NAME}' in result

    def test_render_command_invocation_non_interactive_no_inline_guide(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-task',
            '{PLAN_NAME} {PHASE_NAME}',
            'This guide should not appear',
            requires_user_interaction=False,
        )
        assert 'This guide should not appear' not in result

    def test_render_command_reference(self) -> None:
        assert self.adapter.render_command_reference('respec-task') == '/respec-task'


class TestCodexAdapter:
    def setup_method(self) -> None:
        self.adapter = CodexAdapter()

    def test_commands_dir(self, project_path: Path) -> None:
        assert self.adapter.commands_dir(project_path) == project_path / '.codex' / 'commands'

    def test_prompts_dir(self, project_path: Path) -> None:
        assert self.adapter.prompts_dir(project_path) == project_path / '.codex' / 'agents'

    def test_config_dir_name(self) -> None:
        assert self.adapter.config_dir_name() == '.codex'

    def test_plans_dir(self) -> None:
        assert self.adapter.plans_dir() == '.codex/plans'

    def test_no_adapter_level_commit_instruction_api(self) -> None:
        assert not hasattr(self.adapter, 'loop_commit_instructions')

    def test_selection_prompt_contract_is_explicitly_user_facing(self) -> None:
        assert (
            self.adapter.selection_prompt_instruction
            == 'Present these options directly to the user in the chat UI as a numbered list. This is a user-facing prompt, not an internal instruction. Require a single explicit selection before continuing:'
        )
        assert self.adapter.selection_response_source == 'the user response'

    def test_reasoning_model_raises_when_unconfigured(self, tmp_path: Path) -> None:
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'missing.json'):
            with pytest.raises(RuntimeError, match='models codex'):
                _ = self.adapter.reasoning_model

    def test_reasoning_and_task_model_use_global_mapping(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(
            json.dumps({'codex': {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'}}),
            encoding='utf-8',
        )
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            assert self.adapter.reasoning_model == 'gpt-5.4'
            assert self.adapter.task_model == 'gpt-5.4-mini'

    def test_write_all_creates_skills_and_openai_manifests(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        files = self.adapter.write_all(project_path, [agent_spec], [command_spec])
        assert len(files) == 3
        assert (project_path / '.codex' / 'skills' / 'respec-plan' / 'SKILL.md').exists()
        assert (project_path / '.codex' / 'skills' / 'respec-plan' / 'agents' / 'openai.yaml').exists()
        assert (project_path / '.codex' / 'agents' / 'respec-plan-analyst-agent.toml').exists()
        assert not (project_path / '.codex' / 'skills' / 'respec-plan-analyst-agent').exists()
        assert not (project_path / '.codex' / 'commands' / 'respec-plan.md').exists()
        assert not (project_path / '.codex' / 'agents' / 'respec-plan-analyst.md').exists()

    def test_write_all_cleans_stale_skill_dirs(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        stale_dir = project_path / '.codex' / 'skills' / 'respec-old-skill'
        stale_dir.mkdir(parents=True)
        (stale_dir / 'SKILL.md').write_text('old', encoding='utf-8')

        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        assert not stale_dir.exists()

    def test_count_generated_artifacts_uses_skills_directory(self, project_path: Path) -> None:
        (project_path / '.codex' / 'skills' / 'respec-plan').mkdir(parents=True)
        (project_path / '.codex' / 'skills' / 'respec-plan' / 'SKILL.md').write_text('x', encoding='utf-8')
        (project_path / '.codex' / 'skills' / 'respec-plan-conversation').mkdir(parents=True)
        (project_path / '.codex' / 'skills' / 'respec-plan-conversation' / 'SKILL.md').write_text('x', encoding='utf-8')
        (project_path / '.codex' / 'agents').mkdir(parents=True)
        (project_path / '.codex' / 'agents' / 'respec-plan-analyst-agent.toml').write_text('x', encoding='utf-8')
        (project_path / '.codex' / 'skills' / 'codex-plan-sync').mkdir(parents=True)
        (project_path / '.codex' / 'skills' / 'codex-plan-sync' / 'SKILL.md').write_text('x', encoding='utf-8')

        assert self.adapter.count_generated_commands(project_path) == 2
        assert self.adapter.count_generated_agents(project_path) == 1

    def test_write_all_generates_agent_toml_worker_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        agent_file = project_path / '.codex' / 'agents' / 'respec-plan-analyst-agent.toml'
        content = agent_file.read_text(encoding='utf-8')

        assert 'name = "respec-plan-analyst-agent"' in content
        assert 'sandbox_mode = "workspace-write"' in content
        assert 'developer_instructions = """' in content
        assert 'You are a business analyst.' in content

    def test_command_skill_policy_and_metadata_tiers(self, project_path: Path) -> None:
        command_specs = [
            CommandSpec(
                name='respec-plan',
                description='Plan workflow',
                argument_hint='[plan-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-phase',
                description='Phase workflow',
                argument_hint='[plan-name] [phase-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-code',
                description='Code workflow',
                argument_hint='[plan-name] [phase-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-patch',
                description='Patch workflow',
                argument_hint='[plan-name] [phase-name] [task-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-roadmap',
                description='Roadmap workflow',
                argument_hint='[plan-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-task',
                description='Task workflow',
                argument_hint='[plan-name] [phase-name]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
            CommandSpec(
                name='respec-plan-conversation',
                description='Conversation workflow',
                argument_hint='[optional-context]',
                tools=['Read'],
                body='body',
                delegated_agents=[],
            ),
        ]

        self.adapter.write_all(project_path, [], command_specs)

        for command_name in (
            'respec-plan',
            'respec-phase',
            'respec-code',
            'respec-patch',
            'respec-roadmap',
            'respec-task',
        ):
            policy = (project_path / '.codex' / 'skills' / command_name / 'agents' / 'openai.yaml').read_text(
                encoding='utf-8'
            )
            assert 'allow_implicit_invocation: true' in policy

        conversation_policy = (
            project_path / '.codex' / 'skills' / 'respec-plan-conversation' / 'agents' / 'openai.yaml'
        ).read_text(encoding='utf-8')
        assert 'allow_implicit_invocation: false' in conversation_policy
        assert 'Internal workflow used by `respec-plan`; do not invoke directly.' in conversation_policy

        roadmap_policy = (project_path / '.codex' / 'skills' / 'respec-roadmap' / 'agents' / 'openai.yaml').read_text(
            encoding='utf-8'
        )
        task_policy = (project_path / '.codex' / 'skills' / 'respec-task' / 'agents' / 'openai.yaml').read_text(
            encoding='utf-8'
        )
        roadmap_skill = (project_path / '.codex' / 'skills' / 'respec-roadmap' / 'SKILL.md').read_text(encoding='utf-8')
        task_skill = (project_path / '.codex' / 'skills' / 'respec-task' / 'SKILL.md').read_text(encoding='utf-8')
        conversation_skill = (project_path / '.codex' / 'skills' / 'respec-plan-conversation' / 'SKILL.md').read_text(
            encoding='utf-8'
        )

        assert 'Typically orchestrated by `respec-plan`; direct use is for edge cases.' in roadmap_policy
        assert 'Typically orchestrated by `respec-phase`; direct use is for edge cases.' in task_policy
        assert 'Typically orchestrated by `respec-plan`; direct use is for edge cases.' in roadmap_skill
        assert 'Typically orchestrated by `respec-phase`; direct use is for edge cases.' in task_skill
        assert 'Internal workflow used by `respec-plan`; do not invoke directly.' in conversation_skill
        assert 'Usage: $respec-roadmap [plan-name]' in roadmap_skill
        assert 'Usage: $respec-task [plan-name] [phase-name]' in task_skill
        assert 'Usage:' not in conversation_skill

    def test_register_unregister_mcp_server(self, tmp_path: Path, project_path: Path) -> None:
        codex_home = tmp_path / '.codex'
        with patch.dict('os.environ', {'CODEX_HOME': str(codex_home)}, clear=False):
            assert self.adapter.register_mcp_server(project_path) is True
            assert self.adapter.is_mcp_registered(project_path) is True
            assert self.adapter.unregister_mcp_server(project_path) is True
            assert self.adapter.is_mcp_registered(project_path) is False

    def test_unregister_all_mcp_servers(self, tmp_path: Path, project_path: Path) -> None:
        codex_home = tmp_path / '.codex'
        codex_home.mkdir(parents=True)
        config_path = codex_home / 'config.toml'
        config_path.write_text(
            '[mcp_servers.respec-ai]\ncommand = "respec-ai"\nargs = ["mcp-server"]\n\n'
            '[mcp_servers.respec_ai]\ncommand = "respec-ai"\nargs = ["mcp-server"]\n',
            encoding='utf-8',
        )
        with patch.dict('os.environ', {'CODEX_HOME': str(codex_home)}, clear=False):
            removed = self.adapter.unregister_all_mcp_servers(project_path)
            assert removed == 2
            assert 'respec-ai' not in config_path.read_text(encoding='utf-8')


class TestCodexAdapterInvocationRendering:
    def setup_method(self) -> None:
        self.adapter = CodexAdapter()

    def test_render_agent_invocation_uses_agent_name(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-plan-critic',
            'evaluate strategic plan quality',
            [('plan_name', 'PLAN_NAME')],
        )
        assert 'respec-plan-critic-agent' in result
        assert 'Invoke the `respec-plan-critic-agent` agent' in result
        assert 'plan_name: PLAN_NAME' in result

    def test_render_agent_invocation_dynamic_reviewer(self) -> None:
        result = self.adapter.render_agent_invocation(
            '{REVIEWER}',
            'perform domain-specific code review',
            [('coding_loop_id', 'CODING_LOOP_ID')],
        )
        assert 'respec-{REVIEWER}-agent' in result

    def test_render_agent_invocation_includes_close_guidance(self) -> None:
        result = self.adapter.render_agent_invocation('respec-roadmap', 'generate roadmap', [])
        assert 'close the completed agent' in result

    def test_render_agent_invocation_enforces_isolated_agent_handoff(self) -> None:
        result = self.adapter.render_agent_invocation(
            'respec-patch-planner',
            'generate amendment task document',
            [('task_loop_id', 'PLANNING_LOOP_ID')],
        )
        assert 'Use the rendered runtime agent name exactly.' in result
        assert 'Pass only the listed explicit inputs.' in result
        assert 'Do not rely on any unlisted conversation history or prior thread context.' in result
        assert 'Require the agent to retrieve any additional needed context through its own tools.' in result
        assert 'forked-context' not in result
        assert 'full-history' not in result
        assert 'parent context' not in result
        assert 'inherits' not in result

    def test_parallel_worker_limit_defaults_to_six(self) -> None:
        assert self.adapter.parallel_worker_limit() == 6

    def test_parallel_worker_limit_reads_codex_agents_max_threads(self, tmp_path: Path) -> None:
        codex_home = tmp_path / '.codex'
        codex_home.mkdir(parents=True)
        (codex_home / 'config.toml').write_text('[agents]\nmax_threads = 9\n', encoding='utf-8')
        with patch.dict('os.environ', {'CODEX_HOME': str(codex_home)}, clear=False):
            assert self.adapter.parallel_worker_limit() == 9

    def test_render_parallel_fanout_policy_is_slot_aware(self) -> None:
        result = self.adapter.render_parallel_fanout_policy(
            'create-phase agents',
            'one completion result per roadmap phase',
        )
        assert 'MAX_ACTIVE_WORKERS = 6' in result
        assert 'If spawn fails' in result
        assert 'close it' in result

    def test_render_command_invocation_interactive_returns_guide(self) -> None:
        guide = 'inline guide'
        result = self.adapter.render_command_invocation(
            'respec-plan-conversation',
            '[ARGS]',
            guide,
            requires_user_interaction=True,
        )
        assert result == guide

    def test_render_command_invocation_non_interactive_references_skill(self) -> None:
        result = self.adapter.render_command_invocation(
            'respec-roadmap',
            '{PLAN_NAME}',
            '',
            requires_user_interaction=False,
        )
        assert 'Invoke the `respec-roadmap` skill' in result

    def test_render_command_reference(self) -> None:
        assert self.adapter.render_command_reference('respec-task') == '`respec-task` skill'

    def test_phase_template_step_9_codex_invocation_avoids_nested_backticks(self) -> None:
        template = TemplateCoordinator().generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=self.adapter
        )
        assert 'via `Invoke the `respec-task` skill with:' not in template
        assert 'Attempt task generation in the SAME run via:' in template
        assert (
            'Invoke the `respec-task` skill with: `{PLAN_NAME} {PHASE_NAME} [optional: additional-context]`.'
        ) in template

    def test_codex_generated_templates_do_not_leak_hardcoded_slash_references(self) -> None:
        phase_template = TemplateCoordinator().generate_command_template(
            RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=self.adapter
        )
        task_template = TemplateCoordinator().generate_command_template(
            RespecAICommand.TASK, PlatformType.LINEAR, tui_adapter=self.adapter
        )
        assert '/respec-phase` is the ONLY workflow that runs bp synthesis' not in phase_template
        assert '`respec-phase` skill is the ONLY workflow that runs bp synthesis' in phase_template
        assert '`/respec-task` consumes finalized research artifacts only.' not in task_template
        assert '`respec-task` skill consumes finalized research artifacts only.' in task_template

    def test_codex_code_template_excludes_unused_planning_loop_tools(self) -> None:
        code_template = TemplateCoordinator().generate_command_template(
            RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=self.adapter
        )
        assert 'initialize_planning_loop' not in code_template
        assert 'decide_planning_action' not in code_template
