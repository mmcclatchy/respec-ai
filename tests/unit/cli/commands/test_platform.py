import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from src.cli.commands import platform


class TestPlatformCommand:
    def test_successful_platform_change(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        reRESPEC_AI_dir = tmp_path / '.respec-ai'
        reRESPEC_AI_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (reRESPEC_AI_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.platform.PlatformOrchestrator')
        mocker.patch('src.cli.commands.platform.generate_templates', return_value=([Path('file1.md')], 5, 12))

        args = Namespace(platform='github')
        result = platform.run(args)

        assert result == 0

        config = json.loads((reRESPEC_AI_dir / 'config.json').read_text())
        assert config['platform'] == 'github'

    def test_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        args = Namespace(platform='github')
        result = platform.run(args)

        assert result == 1

    def test_same_platform_no_change(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        reRESPEC_AI_dir = tmp_path / '.respec-ai'
        reRESPEC_AI_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (reRESPEC_AI_dir / 'config.json').write_text(json.dumps(config_data))

        mocker.patch('src.cli.commands.platform.PlatformOrchestrator')
        mock_generate = mocker.patch('src.cli.commands.platform.generate_templates')

        args = Namespace(platform='linear')
        result = platform.run(args)

        assert result == 0
        mock_generate.assert_not_called()

    def test_corrupted_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        reRESPEC_AI_dir = tmp_path / '.respec-ai'
        reRESPEC_AI_dir.mkdir()
        (reRESPEC_AI_dir / 'config.json').write_text('{ invalid json }')

        args = Namespace(platform='github')
        result = platform.run(args)

        assert result == 1

    def test_all_platforms_supported(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        reRESPEC_AI_dir = tmp_path / '.respec-ai'
        reRESPEC_AI_dir.mkdir()

        mocker.patch('src.cli.commands.platform.PlatformOrchestrator')
        mocker.patch('src.cli.commands.platform.generate_templates', return_value=([Path('file1.md')], 5, 12))

        for old_platform, new_platform in [
            ('linear', 'github'),
            ('github', 'markdown'),
            ('markdown', 'linear'),
        ]:
            config_data = {'platform': old_platform, 'version': '0.2.0'}
            (reRESPEC_AI_dir / 'config.json').write_text(json.dumps(config_data))

            args = Namespace(platform=new_platform)
            result = platform.run(args)

            assert result == 0

            config = json.loads((reRESPEC_AI_dir / 'config.json').read_text())
            assert config['platform'] == new_platform
