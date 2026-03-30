import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform.tui_adapters import ClaudeCodeAdapter, get_tui_adapter
from src.platform.tui_adapters.base import AgentSpec, CommandSpec
from src.platform.tui_adapters.opencode import OpenCodeAdapter
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

    def test_from_string(self) -> None:
        assert TuiType('claude-code') == TuiType.CLAUDE_CODE
        assert TuiType('opencode') == TuiType.OPENCODE


class TestGetTuiAdapter:
    def test_returns_claude_code_adapter(self) -> None:
        adapter = get_tui_adapter(TuiType.CLAUDE_CODE)
        assert isinstance(adapter, ClaudeCodeAdapter)

    def test_returns_opencode_adapter(self) -> None:
        adapter = get_tui_adapter(TuiType.OPENCODE)
        assert isinstance(adapter, OpenCodeAdapter)

    def test_invalid_tui_raises(self) -> None:
        with pytest.raises((ValueError, AttributeError)):
            get_tui_adapter('invalid')  # type: ignore[arg-type]


class TestClaudeCodeAdapter:
    def setup_method(self) -> None:
        self.adapter = ClaudeCodeAdapter()

    def test_commands_dir(self, project_path: Path) -> None:
        assert self.adapter.commands_dir(project_path) == project_path / '.claude' / 'commands'

    def test_prompts_dir(self, project_path: Path) -> None:
        assert self.adapter.prompts_dir(project_path) == project_path / '.claude' / 'agents'

    def test_config_dir_name(self) -> None:
        assert self.adapter.config_dir_name() == '.claude'

    def test_reasoning_model(self) -> None:
        assert self.adapter.reasoning_model == 'opus'

    def test_task_model(self) -> None:
        assert self.adapter.task_model == 'sonnet'

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
            with pytest.raises(RuntimeError, match='opencode-models'):
                _ = self.adapter.reasoning_model

    def test_task_model_raises_when_not_configured(self, tmp_path: Path) -> None:
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'missing.json'):
            with pytest.raises(RuntimeError, match='opencode-models'):
                _ = self.adapter.task_model

    def test_render_agent_returns_body(self, agent_spec: AgentSpec) -> None:
        result = self.adapter.render_agent(agent_spec)
        assert result == agent_spec.body
        assert '---' not in result

    def test_render_command_returns_body(self, command_spec: CommandSpec) -> None:
        result = self.adapter.render_command(command_spec)
        assert result == command_spec.body
        assert '---' not in result

    def test_write_all_creates_prompt_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])

        agent_file = project_path / '.opencode' / 'prompts' / 'respec-plan-analyst.md'
        command_file = project_path / '.opencode' / 'prompts' / 'respec-plan.md'
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
        assert config['agent']['respec-plan']['mode'] == 'primary'

    def test_opencode_json_command_entry(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        assert 'respec-plan' in config['command']
        assert config['command']['respec-plan']['agent'] == 'respec-plan'

    def test_opencode_json_prompt_file_reference(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        prompt = config['agent']['respec-plan-analyst']['prompt']
        assert 'respec-plan-analyst.md' in prompt

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
        assert config['agent']['respec-plan']['model'] == 'provider/custom-model'

    def test_opencode_json_builtin_tools_mapped(self, project_path: Path, command_spec: CommandSpec) -> None:
        spec = AgentSpec(
            name='respec-coder',
            description='Coder',
            model='sonnet',
            tools=['Read', 'Write', 'Bash', 'mcp__respec-ai__get_plan'],
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

    def test_opencode_json_task_permissions_on_command(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        self.adapter.write_all(project_path, [agent_spec], [command_spec])
        config = json.loads((project_path / 'opencode.json').read_text())
        plan_agent = config['agent']['respec-plan']
        assert 'permission' in plan_agent
        task_perms = plan_agent['permission']['task']
        assert task_perms.get('*') == 'deny'
        assert task_perms.get('respec-plan-analyst') == 'allow'
        assert task_perms.get('respec-plan-critic') == 'allow'

    def test_write_all_cleans_stale_prompt_files(
        self, project_path: Path, agent_spec: AgentSpec, command_spec: CommandSpec
    ) -> None:
        prompts_dir = project_path / '.opencode' / 'prompts'
        prompts_dir.mkdir(parents=True)
        stale = prompts_dir / 'respec-old-agent.md'
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

    def test_add_mcp_permissions_noop(self) -> None:
        assert self.adapter.add_mcp_permissions() is True
