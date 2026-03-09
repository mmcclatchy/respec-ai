from pathlib import Path

from pytest_mock import MockerFixture

from src.platform.models import ProjectStack
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tooling_defaults import TOOLING_DEFAULTS


class TestGenerateTemplates:
    def test_creates_directories(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        generate_templates(mock_orchestrator, tmp_path, PlatformType.LINEAR)

        assert commands_dir.exists()
        assert agents_dir.exists()

    def test_generates_five_commands(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        assert commands_count == 7
        assert len(list(commands_dir.glob('*.md'))) == 7

    def test_generates_thirteen_agents(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        assert agents_count == 23
        assert len(list(agents_dir.glob('*.md'))) == 23

    def test_returns_file_paths(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        files_written, commands_count, agents_count = generate_templates(
            mock_orchestrator, tmp_path, PlatformType.LINEAR
        )

        assert len(files_written) == 30  # 7 commands + 23 agents = 30
        assert all(isinstance(f, Path) for f in files_written)
        assert all(f.suffix == '.md' for f in files_written)

    def test_works_with_different_platforms(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        for platform in [PlatformType.LINEAR, PlatformType.GITHUB, PlatformType.MARKDOWN]:
            files_written, commands_count, agents_count = generate_templates(mock_orchestrator, tmp_path, platform)

            assert commands_count == 7
            assert agents_count == 23

    def test_passes_tooling_to_agent_templates(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        tooling = {'python': TOOLING_DEFAULTS['python']}

        generate_templates(mock_orchestrator, tmp_path, PlatformType.MARKDOWN, tooling=tooling)

        coder_content = (agents_dir / 'respec-coder.md').read_text()
        quality_checker_content = (agents_dir / 'respec-automated-quality-checker.md').read_text()

        assert 'pytest' in coder_content
        assert 'pytest' in quality_checker_content

    def test_passes_stack_to_agent_templates(self, mocker: MockerFixture, tmp_path: Path) -> None:
        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        mocker.patch(
            'src.platform.template_generator.get_commands_dir',
            return_value=commands_dir,
        )
        mocker.patch(
            'src.platform.template_generator.get_agents_dir',
            return_value=agents_dir,
        )

        mock_orchestrator = mocker.MagicMock()
        mock_orchestrator.template_coordinator.generate_command_template.return_value = '# Command'

        stack = ProjectStack(language='python', backend_framework='fastapi', package_manager='uv')

        generate_templates(mock_orchestrator, tmp_path, PlatformType.MARKDOWN, stack=stack)

        coder_content = (agents_dir / 'respec-coder.md').read_text()
        quality_checker_content = (agents_dir / 'respec-automated-quality-checker.md').read_text()
        code_reviewer_content = (agents_dir / 'respec-code-reviewer.md').read_text()
        phase_architect_content = (agents_dir / 'respec-phase-architect.md').read_text()

        for content in [coder_content, quality_checker_content, code_reviewer_content, phase_architect_content]:
            assert 'PROJECT STACK PROFILE' in content
            assert '**Language**: python' in content
            assert '**Backend Framework**: fastapi' in content
