from argparse import Namespace
from unittest.mock import patch

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
    def test_direct_mapping_saves_without_prompt(self) -> None:
        with patch('src.cli.commands.codex_model.save_global_models') as mock_save:
            result = codex_model.run(
                Namespace(
                    yes=False,
                    aa_key=None,
                    debug=False,
                    no_cache=True,
                    reasoning_model='gpt-5.4',
                    task_model='gpt-5.4-mini',
                )
            )
        assert result == 0
        mock_save.assert_called_once_with(
            {'reasoning': 'gpt-5.4', 'task': 'gpt-5.4-mini'},
            provider='codex',
        )

    def test_yes_mode_uses_suggestion(self) -> None:
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
                )
            )
        assert result == 0
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs.get('provider') == 'codex'
