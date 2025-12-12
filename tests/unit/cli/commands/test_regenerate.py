import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import regenerate


class TestRegenerateCommand:
    def test_successful_regenerate(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.1.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mocker.patch('src.cli.commands.regenerate.generate_templates', return_value=([Path('file1.md')], 5, 12))

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 0

        config = json.loads((respec_ai_dir / 'config.json').read_text())
        assert config['version'] == '0.2.0'

    def test_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 1

    def test_already_up_to_date(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 0

    def test_force_regenerate(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mock_generate = mocker.patch(
            'src.cli.commands.regenerate.generate_templates', return_value=([Path('file1.md')], 5, 12)
        )

        args = Namespace(force=True)
        result = regenerate.run(args)

        assert result == 0
        mock_generate.assert_called_once()

    def test_missing_platform(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'version': '0.1.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 1

    def test_corrupted_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text('{ invalid json }')

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 1

    def test_preserves_platform(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'github', 'version': '0.1.0', 'project_name': 'test'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mocker.patch('src.cli.commands.regenerate.generate_templates', return_value=([Path('file1.md')], 5, 12))

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 0

        config = json.loads((respec_ai_dir / 'config.json').read_text())
        assert config['platform'] == 'github'
        assert config['version'] == '0.2.0'
        assert config['project_name'] == 'test'
