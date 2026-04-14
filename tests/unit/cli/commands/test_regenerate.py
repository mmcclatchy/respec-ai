import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import regenerate


def _write_config(project_path: Path, config: dict[str, str]) -> None:
    respec_ai_dir = project_path / '.respec-ai'
    respec_ai_dir.mkdir(parents=True)
    (respec_ai_dir / 'config.json').write_text(json.dumps(config), encoding='utf-8')


def _touch(path: Path, content: str = 'x') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


class TestRegenerateCommand:
    def test_successful_regenerate(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        _write_config(tmp_path, {'platform': 'linear', 'version': '0.1.0'})
        _touch(tmp_path / '.claude' / 'agents' / 'respec-existing.md')

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mocker.patch('src.cli.commands.regenerate.generate_templates', return_value=([Path('file1.md')], 5, 12))

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 0

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
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

        _write_config(tmp_path, {'platform': 'linear', 'version': '0.2.0'})

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

        _write_config(tmp_path, {'platform': 'linear', 'version': '0.2.0'})
        _touch(tmp_path / '.claude' / 'commands' / 'respec-existing.md')

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

        _write_config(tmp_path, {'version': '0.1.0'})

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 1

    def test_corrupted_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir(parents=True)
        (respec_ai_dir / 'config.json').write_text('{ invalid json }', encoding='utf-8')

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

        _write_config(tmp_path, {'platform': 'github', 'version': '0.1.0', 'plan_name': 'test'})
        _touch(tmp_path / '.claude' / 'agents' / 'respec-existing.md')

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mocker.patch('src.cli.commands.regenerate.generate_templates', return_value=([Path('file1.md')], 5, 12))

        args = Namespace(force=False)
        result = regenerate.run(args)

        assert result == 0

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['platform'] == 'github'
        assert config['version'] == '0.2.0'
        assert config['plan_name'] == 'test'

    def test_no_artifacts_detected_returns_error_and_init_guidance(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'platform': 'linear', 'version': '0.1.0'})
        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')

        result = regenerate.run(Namespace(force=False))

        assert result == 1
        output = capsys.readouterr().out
        assert 'No TUI artifacts detected to regenerate in this project' in output
        assert 'respec-ai init' in output

    def test_detects_multiple_tuis_and_regenerates_all_in_order(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'platform': 'linear', 'version': '0.1.0'})
        _touch(tmp_path / '.claude' / 'agents' / 'respec-existing.md')
        _touch(tmp_path / '.opencode' / 'prompts' / 'commands' / 'respec-existing.md')
        _touch(tmp_path / '.codex' / 'skills' / 'respec-plan' / 'SKILL.md')

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mock_generate = mocker.patch(
            'src.cli.commands.regenerate.generate_templates',
            side_effect=[
                ([Path('claude.md')], 1, 2),
                ([Path('opencode.md')], 3, 4),
                ([Path('codex.md')], 5, 6),
            ],
        )

        result = regenerate.run(Namespace(force=False))

        assert result == 0
        assert mock_generate.call_count == 3
        called_adapters = [call.kwargs['tui_adapter'].display_name for call in mock_generate.call_args_list]
        assert called_adapters == ['Claude Code', 'OpenCode', 'OpenAI Codex']

    def test_partial_failure_continues_and_returns_nonzero(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'platform': 'linear', 'version': '0.1.0'})
        _touch(tmp_path / '.claude' / 'commands' / 'respec-existing.md')
        _touch(tmp_path / '.opencode' / 'prompts' / 'agents' / 'respec-existing.md')

        mocker.patch('src.cli.commands.regenerate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.regenerate.PlatformOrchestrator')
        mocker.patch(
            'src.cli.commands.regenerate.generate_templates',
            side_effect=[([Path('claude.md')], 1, 2), RuntimeError('boom')],
        )

        result = regenerate.run(Namespace(force=False))

        assert result == 1
        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text(encoding='utf-8'))
        assert config['version'] == '0.1.0'
