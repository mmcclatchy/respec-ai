import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.commands import codex_model


class TestCodexModelScoring:
    def test_scores_with_catalog_when_no_aa_data(self) -> None:
        models = ['gpt-5.4', 'gpt-5.4-mini']
        scored = codex_model._score_models(models, {})
        assert len(scored) == 2
        assert all(row['reasoning_score'] > 0 for row in scored)
        assert all(row['task_score'] > 0 for row in scored)

    def test_suggests_reasoning_and_task(self) -> None:
        scored = [
            {
                'model_id': 'gpt-5.4',
                'intelligence': 90.0,
                'coding': 70.0,
                'reasoning_score': 90.0,
                'task_score': 70.0,
                'insight': 'x',
            },
            {
                'model_id': 'gpt-5.4-mini',
                'intelligence': 60.0,
                'coding': 80.0,
                'reasoning_score': 60.0,
                'task_score': 80.0,
                'insight': 'y',
            },
        ]
        result = codex_model._suggest_tiers(scored)
        assert result == {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'}


class TestCodexModelRun:
    def test_direct_mapping_saves_without_prompt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with patch('src.cli.commands.codex_model.save_global_models') as mock_save:
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
                    no_apply=True,
                )
            )
        assert result == 0
        mock_save.assert_called_once_with(
            {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'},
            provider='codex',
        )

    def test_yes_mode_uses_suggestion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with (
            patch('src.cli.commands.codex_model._fetch_aa_data', return_value={}),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(
                Namespace(
                    yes=True,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model=None,
                    task_model=None,
                    no_apply=True,
                )
            )
        assert result == 0
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs.get('provider') == 'codex'

    def test_auto_apply_runs_forced_regenerate_in_codex_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir(parents=True)
        (config_dir / 'config.json').write_text(json.dumps({'platform': 'markdown', 'tui': 'codex'}), encoding='utf-8')

        with (
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=0) as mock_regen,
        ):
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
                    no_apply=False,
                )
            )
        assert result == 0
        mock_regen.assert_called_once_with()

    def test_auto_apply_skips_when_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with (
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate') as mock_regen,
        ):
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
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
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=0) as mock_regen,
        ):
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
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
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate') as mock_regen,
        ):
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
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
            patch('src.cli.commands.codex_model.save_global_models'),
            patch('src.cli.commands.codex_model._run_forced_regenerate', return_value=1),
        ):
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
                    no_apply=False,
                )
            )
        assert result == 1
