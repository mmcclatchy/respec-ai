from pathlib import Path

from pytest_mock import MockerFixture

from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates


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

        assert commands_count == 5
        assert len(list(commands_dir.glob('*.md'))) == 5

    def test_generates_twelve_agents(self, mocker: MockerFixture, tmp_path: Path) -> None:
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

        assert agents_count == 12
        assert len(list(agents_dir.glob('*.md'))) == 12

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

        assert len(files_written) == 17
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

            assert commands_count == 5
            assert agents_count == 12
