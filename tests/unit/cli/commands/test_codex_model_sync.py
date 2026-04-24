import json
import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.commands import codex_model


def _discovered_models() -> list[dict[str, object]]:
    return [
        {
            'id': 'gpt-example-a',
            'display_name': 'GPT Example A',
            'description': 'Example model A.',
            'hidden': False,
            'is_default': True,
        },
        {
            'id': 'gpt-example-b',
            'display_name': 'GPT Example B',
            'description': 'Example model B.',
            'hidden': False,
            'is_default': False,
        },
    ]


def _args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        'aa_key': None,
        'debug': False,
        'no_cache': True,
        'include_hidden': False,
        'update_codex': False,
        'no_update_codex': True,
        'reasoning_model': None,
        'orchestration_model': None,
        'task_model': None,
        'coding_model': None,
        'review_model': None,
        'no_apply': True,
    }
    values.update(overrides)
    return Namespace(**values)


class TestCodexModelRun:
    def test_direct_mapping_requires_all_four_models(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                )
            )

        assert result == 0
        mock_save.assert_called_once_with(
            {
                'reasoning': 'gpt-example-a',
                'orchestration': 'gpt-example-b',
                'coding': 'gpt-example-a',
                'review': 'gpt-example-b',
            },
            provider='codex',
        )

    def test_direct_mapping_fails_when_any_tier_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch('src.cli.commands.codex_model.save_global_models') as mock_save:
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model=None,
                )
            )

        assert result == 1
        mock_save.assert_not_called()

    def test_manual_no_aa_flow_uses_discovery_order_and_skips_metrics(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)

        with (
            patch('src.cli.commands.codex_model.load_api_key', return_value=''),
            patch('src.cli.commands.codex_model._discover_codex_models', return_value=_discovered_models()),
            patch('src.cli.commands.codex_model._fetch_aa_data') as mock_fetch_aa,
            patch('src.cli.commands.codex_model._display_aa_table') as mock_display_aa,
            patch('src.cli.commands.codex_model.console.input', side_effect=['1', '2', '1', '2', '']),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(_args(no_update_codex=True))

        assert result == 0
        mock_fetch_aa.assert_not_called()
        mock_display_aa.assert_not_called()
        mock_save.assert_called_once_with(
            {
                'reasoning': 'gpt-example-a',
                'orchestration': 'gpt-example-b',
                'coding': 'gpt-example-a',
                'review': 'gpt-example-b',
            },
            provider='codex',
        )

    def test_manual_aa_flow_displays_metrics_but_saves_prompted_mapping(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        aa_data = {
            'gpt example a': {
                codex_model._REASONING_INDEX: 70.0,
                codex_model._CODING_INDEX: 65.0,
            }
        }

        with (
            patch('src.cli.commands.codex_model._discover_codex_models', return_value=_discovered_models()),
            patch('src.cli.commands.codex_model._fetch_aa_data', return_value=aa_data) as mock_fetch_aa,
            patch('src.cli.commands.codex_model._display_aa_table') as mock_display_aa,
            patch('src.cli.commands.codex_model.console.input', side_effect=['2', '2', '1', '1', '']),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(_args(aa_key='aa-key', no_update_codex=True))

        assert result == 0
        mock_fetch_aa.assert_called_once_with('aa-key', debug=False)
        mock_display_aa.assert_called_once_with(_discovered_models(), aa_data)
        mock_save.assert_called_once_with(
            {
                'reasoning': 'gpt-example-b',
                'orchestration': 'gpt-example-b',
                'coding': 'gpt-example-a',
                'review': 'gpt-example-a',
            },
            provider='codex',
        )

    def test_update_codex_flag_runs_npm_before_discovery(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)

        with (
            patch('src.cli.commands.codex_model.load_api_key', return_value=''),
            patch(
                'src.cli.commands.codex_model.subprocess.run',
                return_value=subprocess.CompletedProcess(codex_model._CODEX_UPDATE_CMD, 0),
            ) as mock_run,
            patch('src.cli.commands.codex_model._discover_codex_models', return_value=_discovered_models()),
            patch('src.cli.commands.codex_model.console.input', side_effect=['1', '1', '1', '1', '']),
            patch('src.cli.commands.codex_model.save_global_models'),
        ):
            result = codex_model.run(_args(update_codex=True, no_update_codex=False))

        assert result == 0
        mock_run.assert_called_once_with(codex_model._CODEX_UPDATE_CMD)

    def test_update_prompt_can_be_declined_without_running_npm(self) -> None:
        with (
            patch('src.cli.commands.codex_model.console.input', return_value='n'),
            patch('src.cli.commands.codex_model.subprocess.run') as mock_run,
        ):
            result = codex_model._maybe_update_codex_cli(_args(no_update_codex=False))

        assert result is True
        mock_run.assert_not_called()

    def test_returns_1_when_model_discovery_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)
        with (
            patch('src.cli.commands.codex_model.load_api_key', return_value=''),
            patch('src.cli.commands.codex_model._discover_codex_models', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(_args(no_update_codex=True))

        assert result == 1
        mock_save.assert_not_called()

    def test_auto_apply_runs_forced_regenerate_in_codex_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir(parents=True)
        (config_dir / 'config.json').write_text(json.dumps({'platform': 'markdown', 'tui': 'codex'}), encoding='utf-8')

        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=0) as mock_regen,
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                    no_apply=False,
                )
            )
        assert result == 0
        mock_regen.assert_called_once_with()

    def test_auto_apply_skips_when_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate') as mock_regen,
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                    no_apply=False,
                )
            )
        assert result == 0
        mock_regen.assert_not_called()

    def test_auto_apply_runs_even_when_project_tui_is_not_codex(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir(parents=True)
        (config_dir / 'config.json').write_text(
            json.dumps({'platform': 'markdown', 'tui': 'claude-code'}),
            encoding='utf-8',
        )

        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=0) as mock_regen,
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                    no_apply=False,
                )
            )
        assert result == 0
        mock_regen.assert_called_once_with()

    def test_no_apply_suppresses_forced_regenerate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir(parents=True)
        (config_dir / 'config.json').write_text(json.dumps({'platform': 'markdown', 'tui': 'codex'}), encoding='utf-8')

        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate') as mock_regen,
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                    no_apply=True,
                )
            )
        assert result == 0
        mock_regen.assert_not_called()

    def test_auto_apply_returns_nonzero_when_regenerate_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir(parents=True)
        (config_dir / 'config.json').write_text(json.dumps({'platform': 'markdown', 'tui': 'codex'}), encoding='utf-8')

        with (
            patch('src.cli.commands.codex_model._cached_discovered_model_ids', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=1),
        ):
            result = codex_model.run(
                _args(
                    reasoning_model='gpt-example-a',
                    orchestration_model='gpt-example-b',
                    coding_model='gpt-example-a',
                    review_model='gpt-example-b',
                    no_apply=False,
                )
            )
        assert result == 1


class TestCodexModelDiscovery:
    def test_discover_uses_live_models_and_filters_hidden(self) -> None:
        live = [
            {
                'id': 'gpt-example-a',
                'displayName': 'GPT Example A',
                'description': 'Example model.',
                'hidden': False,
                'isDefault': True,
            },
            {
                'id': 'gpt-example-hidden',
                'displayName': 'GPT Example Hidden',
                'description': 'Hidden example model.',
                'hidden': True,
                'isDefault': False,
            },
        ]
        with (
            patch(
                'src.cli.commands.codex_model._fetch_codex_models_live',
                return_value=codex_model._normalize_discovered_models(live),
            ),
            patch('src.cli.commands.codex_model._write_cache') as mock_cache,
        ):
            visible = codex_model._discover_codex_models(include_hidden=False, debug=False)
            all_models = codex_model._discover_codex_models(include_hidden=True, debug=False)

        assert [m['id'] for m in visible] == ['gpt-example-a']
        assert [m['id'] for m in all_models] == ['gpt-example-a', 'gpt-example-hidden']
        assert mock_cache.call_count == 2

    def test_discover_falls_back_to_cache_when_live_fails(self) -> None:
        cached = [
            {
                'id': 'gpt-example-a',
                'display_name': 'GPT Example A',
                'description': 'Example model.',
                'hidden': False,
                'is_default': True,
            },
            {
                'id': 'gpt-example-hidden',
                'display_name': 'GPT Example Hidden',
                'description': 'Hidden example model.',
                'hidden': True,
                'is_default': False,
            },
        ]
        with (
            patch('src.cli.commands.codex_model._fetch_codex_models_live', side_effect=RuntimeError('boom')),
            patch('src.cli.commands.codex_model._read_cache', return_value=cached),
        ):
            models = codex_model._discover_codex_models(include_hidden=False, debug=False)
        assert [m['id'] for m in models] == ['gpt-example-a']

    def test_discover_returns_empty_without_live_or_cache(self) -> None:
        with (
            patch('src.cli.commands.codex_model._fetch_codex_models_live', side_effect=RuntimeError('boom')),
            patch('src.cli.commands.codex_model._read_cache', return_value=None),
        ):
            models = codex_model._discover_codex_models(include_hidden=False, debug=False)
        assert models == []
