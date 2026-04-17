import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.commands import codex_model


class TestCodexModelScoring:
    def test_scores_with_local_priors_when_no_aa_data(self) -> None:
        models = ['gpt-5.4', 'gpt-5.4-mini']
        scored = codex_model._score_models(models, {})
        assert len(scored) == 2
        assert all(row['reasoning_score'] > 0 for row in scored)
        assert all(row['task_score'] > 0 for row in scored)

    def test_scores_unknown_model_with_dynamic_priors(self) -> None:
        scored = codex_model._score_models(
            ['gpt-5.9-codex-spark'],
            {},
            model_metadata={
                'gpt-5.9-codex-spark': {
                    'description': 'Ultra-fast coding model.',
                    'display_name': 'GPT-5.9-Codex-Spark',
                    'hidden': False,
                    'is_default': False,
                }
            },
        )
        assert len(scored) == 1
        assert scored[0]['model_id'] == 'gpt-5.9-codex-spark'
        assert scored[0]['reasoning_score'] > 0
        assert scored[0]['task_score'] > 0

    def test_suggests_reasoning_and_task(self) -> None:
        scored = [
            {
                'model_id': 'gpt-5.4',
                'intelligence': 90.0,
                'coding': 70.0,
                'has_aa_capability': True,
                'has_aa_speed': True,
                'reasoning_score': 90.0,
                'task_score': 70.0,
                'insight': 'x',
            },
            {
                'model_id': 'gpt-5.4-mini',
                'intelligence': 60.0,
                'coding': 80.0,
                'has_aa_capability': True,
                'has_aa_speed': True,
                'reasoning_score': 60.0,
                'task_score': 80.0,
                'insight': 'y',
            },
        ]
        result = codex_model._suggest_tiers(scored)
        assert result == {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'}

    def test_suggestion_uses_aa_backed_models_when_available(self) -> None:
        scored = [
            {
                'model_id': 'gpt-5.3-codex-spark',
                'intelligence': 0.0,
                'coding': 0.0,
                'has_aa_capability': False,
                'has_aa_speed': False,
                'reasoning_score': 99.0,
                'task_score': 99.0,
                'insight': 'inferred',
            },
            {
                'model_id': 'gpt-5.3-codex',
                'intelligence': 53.6,
                'coding': 53.1,
                'has_aa_capability': True,
                'has_aa_speed': True,
                'reasoning_score': 53.6,
                'task_score': 53.1,
                'insight': 'aa codex',
            },
            {
                'model_id': 'gpt-5.4',
                'intelligence': 56.8,
                'coding': 57.3,
                'has_aa_capability': True,
                'has_aa_speed': True,
                'reasoning_score': 56.8,
                'task_score': 57.3,
                'insight': 'aa',
            },
        ]
        result = codex_model._suggest_tiers(scored)
        assert result == {'reasoning': 'gpt-5.4', 'task': 'gpt-5.3-codex'}

    def test_reasoning_fallback_excludes_mini_and_spark(self) -> None:
        result = codex_model._pick_reasoning_fallback(
            ['gpt-5.4-mini', 'gpt-5.3-codex-spark', 'gpt-5.2-codex', 'gpt-5.4']
        )
        assert result == 'gpt-5.4'

    def test_task_fallback_prefers_base_codex(self) -> None:
        result = codex_model._pick_task_codex_fallback(
            ['gpt-5.3-codex-spark', 'gpt-5.2-codex', 'gpt-5.1-codex-max', 'gpt-5.4']
        )
        assert result == 'gpt-5.2-codex'

    def test_version_parsing_is_semantic_not_float(self) -> None:
        candidates = ['gpt-5.9-codex', 'gpt-5.10-codex']
        best = max(candidates, key=codex_model._fallback_sort_key)
        assert best == 'gpt-5.10-codex'


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
            patch(
                'src.cli.commands.codex_model._discover_codex_models',
                return_value=[
                    {
                        'id': 'gpt-5.4',
                        'display_name': 'gpt-5.4',
                        'description': 'Latest frontier agentic coding model.',
                        'hidden': False,
                        'is_default': True,
                    },
                    {
                        'id': 'gpt-5.4-mini',
                        'display_name': 'gpt-5.4-mini',
                        'description': 'Smaller frontier agentic coding model.',
                        'hidden': False,
                        'is_default': False,
                    },
                ],
            ),
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

    def test_returns_1_when_model_discovery_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with (
            patch('src.cli.commands.codex_model._discover_codex_models', return_value=[]),
            patch('src.cli.commands.codex_model.save_global_models') as mock_save,
        ):
            result = codex_model.run(
                Namespace(
                    yes=True,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    include_hidden=False,
                    reasoning_model=None,
                    task_model=None,
                    no_apply=True,
                )
            )
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


class TestCodexModelDiscovery:
    def test_discover_uses_live_models_and_filters_hidden(self) -> None:
        live = [
            {
                'id': 'gpt-5.4',
                'displayName': 'gpt-5.4',
                'description': 'Latest frontier agentic coding model.',
                'hidden': False,
                'isDefault': True,
            },
            {
                'id': 'gpt-5.1-codex',
                'displayName': 'gpt-5.1-codex',
                'description': 'Legacy codex model.',
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

        assert [m['id'] for m in visible] == ['gpt-5.4']
        assert [m['id'] for m in all_models] == ['gpt-5.4', 'gpt-5.1-codex']
        assert mock_cache.call_count == 2

    def test_discover_falls_back_to_cache_when_live_fails(self) -> None:
        cached = [
            {
                'id': 'gpt-5.4',
                'display_name': 'gpt-5.4',
                'description': 'Latest frontier agentic coding model.',
                'hidden': False,
                'is_default': True,
            },
            {
                'id': 'gpt-5.1-codex',
                'display_name': 'gpt-5.1-codex',
                'description': 'Legacy codex model.',
                'hidden': True,
                'is_default': False,
            },
        ]
        with (
            patch('src.cli.commands.codex_model._fetch_codex_models_live', side_effect=RuntimeError('boom')),
            patch('src.cli.commands.codex_model._read_cache', return_value=cached),
        ):
            models = codex_model._discover_codex_models(include_hidden=False, debug=False)
        assert [m['id'] for m in models] == ['gpt-5.4']

    def test_discover_returns_empty_without_live_or_cache(self) -> None:
        with (
            patch('src.cli.commands.codex_model._fetch_codex_models_live', side_effect=RuntimeError('boom')),
            patch('src.cli.commands.codex_model._read_cache', return_value=None),
        ):
            models = codex_model._discover_codex_models(include_hidden=False, debug=False)
        assert models == []
