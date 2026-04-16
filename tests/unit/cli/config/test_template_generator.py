import json
from pathlib import Path
from unittest.mock import patch

from pytest_mock import MockerFixture

from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


_MOCK_COMMAND_CONTENT = '---\nallowed-tools: Read\nargument-hint: [plan-name]\ndescription: A command\n---\n\n# Command'


class TestGenerateTemplates:
    def test_creates_directories(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR)

        assert (tmp_path / '.claude' / 'commands').exists()
        assert (tmp_path / '.claude' / 'agents').exists()

    def test_generates_commands(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        commands_dir = tmp_path / '.claude' / 'commands'
        assert commands_count == 8
        assert len(list(commands_dir.glob('*.md'))) == 8
        assert (commands_dir / 'respec-standards.md').exists()

    def test_generates_thirteen_agents(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        agents_dir = tmp_path / '.claude' / 'agents'
        assert agents_count == 21
        assert len(list(agents_dir.glob('*.md'))) == 21

    def test_returns_file_paths(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        assert len(files_written) == 29  # 8 commands + 21 agents = 29
        assert all(isinstance(f, Path) for f in files_written)
        assert all(f.suffix == '.md' for f in files_written)

    def test_works_with_different_platforms(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        for platform in [PlatformType.LINEAR, PlatformType.GITHUB, PlatformType.MARKDOWN]:
            files_written, commands_count, agents_count = generate_templates(mock_orchestrator, tmp_path, platform)

            assert commands_count == 8
            assert agents_count == 21

    def test_removes_stale_respec_files_before_writing(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / '.claude' / 'commands'
        agents_dir = tmp_path / '.claude' / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        stale_agent = agents_dir / 'respec-task-coder.md'
        stale_command = commands_dir / 'respec-old-command.md'
        non_respec_agent = agents_dir / 'my-custom-agent.md'
        stale_agent.write_text('stale')
        stale_command.write_text('stale')
        non_respec_agent.write_text('keep me')

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR)

        assert not stale_agent.exists()
        assert not stale_command.exists()
        assert non_respec_agent.exists()

    def test_reasoning_commands_get_reasoning_model_in_opencode_json(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT
        adapter = get_tui_adapter(TuiType.OPENCODE)
        models_data = {'opencode': {'reasoning': 'provider/reasoning-model', 'task': 'provider/task-model'}}

        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'models.json'):
            (tmp_path / 'models.json').write_text(json.dumps(models_data), encoding='utf-8')
            generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR, tui_adapter=adapter)

        config = json.loads((tmp_path / 'opencode.json').read_text())
        assert config['agent']['cmd-respec-plan']['model'] == 'provider/reasoning-model'
        assert config['agent']['cmd-respec-plan-conversation']['model'] == 'provider/reasoning-model'

    def test_task_commands_get_task_model_in_opencode_json(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT
        adapter = get_tui_adapter(TuiType.OPENCODE)
        models_data = {'opencode': {'reasoning': 'provider/reasoning-model', 'task': 'provider/task-model'}}

        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'models.json'):
            (tmp_path / 'models.json').write_text(json.dumps(models_data), encoding='utf-8')
            generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR, tui_adapter=adapter)

        config = json.loads((tmp_path / 'opencode.json').read_text())
        for name in ('respec-phase', 'respec-task', 'respec-code', 'respec-patch', 'respec-roadmap', 'respec-standards'):
            assert config['agent'][f'cmd-{name}']['model'] == 'provider/task-model'

    def test_templates_include_project_configuration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT

        generate_templates(mock_orchestrator, tmp_path, PlatformType.MARKDOWN)

        agents_dir = tmp_path / '.claude' / 'agents'
        coder_content = (agents_dir / 'respec-coder.md').read_text()
        quality_checker_content = (agents_dir / 'respec-automated-quality-checker.md').read_text()

        assert 'PROJECT CONFIGURATION' in coder_content
        assert '.respec-ai/config/stack.toml' in coder_content
        assert 'PROJECT CONFIGURATION' in quality_checker_content
        assert '.respec-ai/config/stack.toml' in quality_checker_content

    def test_generates_codex_artifacts(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT
        adapter = get_tui_adapter(TuiType.CODEX)

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR, tui_adapter=adapter
        )

        assert commands_count == 8
        assert agents_count == 21
        assert (tmp_path / '.codex' / 'skills' / 'respec-standards' / 'SKILL.md').exists()
        assert (tmp_path / '.codex' / 'skills' / 'respec-plan' / 'SKILL.md').exists()
        assert (tmp_path / '.codex' / 'skills' / 'respec-plan' / 'agents' / 'openai.yaml').exists()
        assert (tmp_path / '.codex' / 'agents' / 'respec-plan-analyst-agent.toml').exists()
        assert not (tmp_path / '.codex' / 'skills' / 'respec-plan-analyst-agent').exists()
        assert not (tmp_path / '.codex' / 'commands' / 'respec-plan.md').exists()
        assert not (tmp_path / '.codex' / 'agents' / 'respec-plan-analyst.md').exists()
        assert any('SKILL.md' in str(p) for p in files_written)

    def test_codex_model_tiers_propagate_to_skill_and_agent_artifacts(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = _MOCK_COMMAND_CONTENT
        adapter = get_tui_adapter(TuiType.CODEX)
        models_data = {'codex': {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'}}

        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'models.json'):
            (tmp_path / 'models.json').write_text(json.dumps(models_data), encoding='utf-8')
            generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR, tui_adapter=adapter)

        plan_skill = (tmp_path / '.codex' / 'skills' / 'respec-plan' / 'SKILL.md').read_text(encoding='utf-8')
        code_skill = (tmp_path / '.codex' / 'skills' / 'respec-code' / 'SKILL.md').read_text(encoding='utf-8')
        phase_architect_agent = (tmp_path / '.codex' / 'agents' / 'respec-phase-architect-agent.toml').read_text(
            encoding='utf-8'
        )
        coder_agent = (tmp_path / '.codex' / 'agents' / 'respec-coder-agent.toml').read_text(encoding='utf-8')
        plan_openai_yaml = (tmp_path / '.codex' / 'skills' / 'respec-plan' / 'agents' / 'openai.yaml').read_text(
            encoding='utf-8'
        )

        assert 'Model: gpt-5.4' in plan_skill
        assert 'Model: gpt-5.4-mini' in code_skill
        assert 'model = "gpt-5.4"' in phase_architect_agent
        assert 'model = "gpt-5.4-mini"' in coder_agent
        assert '\nmodel:' not in plan_openai_yaml
