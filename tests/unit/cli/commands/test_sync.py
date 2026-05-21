import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import sync


def _write_config(project_path: Path, config: dict) -> None:
    respec_ai_dir = project_path / '.respec-ai'
    respec_ai_dir.mkdir(parents=True, exist_ok=True)
    (respec_ai_dir / 'config.json').write_text(json.dumps(config), encoding='utf-8')
    config_dir = respec_ai_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    (config_dir / 'stack.toml').write_text('schema_version = 2\n', encoding='utf-8')


class TestSyncCommand:
    def test_not_initialized_returns_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        args = Namespace(
            platform=None,
            tui=None,
            skip_mcp_registration=True,
            skip_best_practices_setup=True,
            pin_models=False,
            yes=True,
            aa_key=None,
            exa_key=None,
        )
        result = sync.run(args)
        assert result == 1

    def test_initialized_project_missing_config_dir_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir(parents=True, exist_ok=True)
        (respec_ai_dir / 'config.json').write_text(
            json.dumps({'project_name': 'demo', 'platform': 'markdown', 'tui': 'claude-code'}),
            encoding='utf-8',
        )

        args = Namespace(
            platform=None,
            tui=None,
            skip_mcp_registration=True,
            skip_best_practices_setup=True,
            pin_models=False,
            yes=True,
            aa_key=None,
            exa_key=None,
        )
        result = sync.run(args)
        assert result == 1

    def test_uses_existing_platform_and_tui_when_not_provided(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'project_name': 'demo', 'platform': 'markdown', 'tui': 'claude-code', 'x': 'keep'})

        mock_adapter = mocker.MagicMock()
        mock_adapter.display_name = 'Claude Code'
        mock_adapter.render_command_invocation.side_effect = lambda *_args, **_kwargs: '/dummy'
        mocker.patch('src.cli.commands.sync.get_tui_adapter', return_value=mock_adapter)
        mocker.patch('src.cli.commands.sync.PlatformOrchestrator')
        mocker.patch('src.cli.commands.sync.run_tui_model_setup', return_value=0)
        mocker.patch('src.cli.commands.sync.generate_templates', return_value=([Path('a.md')], 1, 1))
        mocker.patch('src.cli.commands.sync._setup_mcp_server', return_value=False)
        mocker.patch('src.cli.commands.sync.ensure_best_practices_ready', return_value=True)
        mocker.patch('src.cli.commands.sync.print_setup_complete')
        mocker.patch('src.cli.commands.sync.get_package_version', return_value='0.2.0')

        args = Namespace(
            platform=None,
            tui=None,
            skip_mcp_registration=True,
            skip_best_practices_setup=True,
            pin_models=False,
            yes=True,
            aa_key=None,
            exa_key=None,
        )
        result = sync.run(args)

        assert result == 0
        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text(encoding='utf-8'))
        assert config['platform'] == 'markdown'
        assert config['tui'] == 'claude-code'
        assert config['version'] == '0.2.0'
        assert config['x'] == 'keep'

    def test_pin_models_writes_project_override(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'project_name': 'demo', 'platform': 'markdown', 'tui': 'codex'})

        mock_adapter = mocker.MagicMock()
        mock_adapter.display_name = 'OpenAI Codex'
        mock_adapter.render_command_invocation.side_effect = lambda *_args, **_kwargs: '$dummy'
        mocker.patch('src.cli.commands.sync.get_tui_adapter', return_value=mock_adapter)
        mocker.patch('src.cli.commands.sync.PlatformOrchestrator')
        mocker.patch('src.cli.commands.sync.run_tui_model_setup', return_value=0)
        mocker.patch('src.cli.commands.sync.generate_templates', return_value=([Path('a.md')], 1, 1))
        mocker.patch('src.cli.commands.sync._setup_mcp_server', return_value=False)
        mocker.patch('src.cli.commands.sync.ensure_best_practices_ready', return_value=True)
        mocker.patch('src.cli.commands.sync.print_setup_complete')
        mocker.patch('src.cli.commands.sync.load_global_models', return_value={'reasoning': 'gpt-x'})

        args = Namespace(
            platform=None,
            tui='codex',
            skip_mcp_registration=True,
            skip_best_practices_setup=True,
            pin_models=True,
            yes=True,
            aa_key=None,
            exa_key=None,
        )
        result = sync.run(args)
        assert result == 0

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text(encoding='utf-8'))
        assert config['models']['codex']['reasoning'] == 'gpt-x'

    def test_preflight_failure_returns_nonzero(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, {'project_name': 'demo', 'platform': 'markdown', 'tui': 'claude-code'})

        mock_adapter = mocker.MagicMock()
        mock_adapter.display_name = 'Claude Code'
        mock_adapter.render_command_invocation.side_effect = lambda *_args, **_kwargs: '/dummy'
        mocker.patch('src.cli.commands.sync.get_tui_adapter', return_value=mock_adapter)
        mocker.patch('src.cli.commands.sync.PlatformOrchestrator')
        mocker.patch('src.cli.commands.sync.run_tui_model_setup', return_value=0)
        mocker.patch('src.cli.commands.sync.generate_templates', return_value=([Path('a.md')], 1, 1))
        mocker.patch('src.cli.commands.sync._setup_mcp_server', return_value=False)
        mocker.patch('src.cli.commands.sync.ensure_best_practices_ready', return_value=False)
        mocker.patch('src.cli.commands.sync.print_setup_complete')

        args = Namespace(
            platform=None,
            tui=None,
            skip_mcp_registration=True,
            skip_best_practices_setup=False,
            pin_models=False,
            yes=True,
            aa_key=None,
            exa_key=None,
        )
        result = sync.run(args)
        assert result == 1
