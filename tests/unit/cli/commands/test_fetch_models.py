import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from src.cli.commands import fetch_models
from src.cli.commands.fetch_models import (
    _fetch_benchmark_evidence,
    _fetch_go_plan_models,
    _key_finding,
    _rank_models,
    _score_model,
)


import urllib.error


class TestFetchGoPlanModels:
    def test_returns_model_ids_from_html(self) -> None:
        html = '<p>Use opencode-go/kimi-k2.5 or opencode-go/minimax-m2.7 for best results.</p>'
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = html.encode('utf-8')

        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = _fetch_go_plan_models()

        assert result == ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']

    def test_deduplicates_model_ids(self) -> None:
        html = 'opencode-go/kimi-k2.5 opencode-go/kimi-k2.5 opencode-go/minimax-m2.7'
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = html.encode('utf-8')

        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = _fetch_go_plan_models()

        assert result == ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']

    def test_returns_empty_on_network_error(self) -> None:
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('timeout')):
            result = _fetch_go_plan_models()

        assert result == []

    def test_returns_empty_when_no_models_in_html(self) -> None:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'<p>No models here</p>'

        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = _fetch_go_plan_models()

        assert result == []


class TestFetchBenchmarkEvidence:
    def _make_resp(self, data: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(data).encode('utf-8')
        return mock_resp

    def test_returns_evidence_per_model(self) -> None:
        exa_response = {
            'results': [
                {
                    'title': 'Kimi K2.5 AIME benchmark results',
                    'text': 'Scored 82.3 on AIME 2025',
                    'publishedDate': '2026-01-15T00:00:00Z',
                    'url': 'https://example.com',
                }
            ]
        }
        with patch('urllib.request.urlopen', return_value=self._make_resp(exa_response)):
            result = _fetch_benchmark_evidence(['opencode-go/kimi-k2.5'], 'test-key')

        assert 'opencode-go/kimi-k2.5' in result
        entries = result['opencode-go/kimi-k2.5']
        assert len(entries) == 1
        assert entries[0]['title'] == 'Kimi K2.5 AIME benchmark results'
        assert entries[0]['published'] == '2026-01-15'

    def test_truncates_snippet_to_200_chars(self) -> None:
        long_text = 'x' * 300
        exa_response = {'results': [{'title': 'T', 'text': long_text, 'publishedDate': '', 'url': ''}]}
        with patch('urllib.request.urlopen', return_value=self._make_resp(exa_response)):
            result = _fetch_benchmark_evidence(['opencode-go/kimi-k2.5'], 'test-key')

        assert len(result['opencode-go/kimi-k2.5'][0]['snippet']) == 200

    def test_falls_back_to_summary_when_no_text(self) -> None:
        exa_response = {
            'results': [{'title': 'T', 'text': None, 'summary': 'summary text', 'publishedDate': '', 'url': ''}]
        }
        with patch('urllib.request.urlopen', return_value=self._make_resp(exa_response)):
            result = _fetch_benchmark_evidence(['opencode-go/kimi-k2.5'], 'test-key')

        assert result['opencode-go/kimi-k2.5'][0]['snippet'] == 'summary text'

    def test_returns_empty_list_on_network_error(self) -> None:
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('err')):
            result = _fetch_benchmark_evidence(['opencode-go/kimi-k2.5'], 'test-key')

        assert result['opencode-go/kimi-k2.5'] == []

    def test_returns_empty_list_on_invalid_json(self) -> None:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'not json'

        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = _fetch_benchmark_evidence(['opencode-go/kimi-k2.5'], 'test-key')

        assert result['opencode-go/kimi-k2.5'] == []


class TestScoreModel:
    def test_counts_reasoning_signals(self) -> None:
        results = [{'title': 'AIME math competition results', 'snippet': 'SWE-bench score 49%'}]
        reasoning, instruction, speed = _score_model('opencode-go/kimi-k2.5', results)
        assert reasoning >= 2

    def test_counts_instruction_signals(self) -> None:
        results = [{'title': 'IFEval MT-bench results', 'snippet': 'instruction follow score 91'}]
        _, instruction, _ = _score_model('opencode-go/minimax-m2.7', results)
        assert instruction >= 2

    def test_counts_speed_signals(self) -> None:
        results = [{'title': 'Fast efficient model', 'snippet': '180 tok/s throughput'}]
        _, _, speed = _score_model('opencode-go/minimax-m2.5', results)
        assert speed >= 2

    def test_returns_zeros_for_empty_results(self) -> None:
        assert _score_model('opencode-go/kimi-k2.5', []) == (0, 0, 0)


class TestRankModels:
    def test_assigns_tiers_by_index_without_evidence(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7', 'opencode-go/minimax-m2.5']
        result = _rank_models(models, {})
        assert result == {
            'opus': 'opencode-go/kimi-k2.5',
            'sonnet': 'opencode-go/minimax-m2.7',
            'haiku': 'opencode-go/minimax-m2.5',
        }

    def test_assigns_only_available_tiers_without_evidence(self) -> None:
        models = ['opencode-go/kimi-k2.5']
        result = _rank_models(models, {})
        assert result == {'opus': 'opencode-go/kimi-k2.5'}
        assert 'sonnet' not in result

    def test_assigns_opus_to_highest_reasoning_score(self) -> None:
        models = ['opencode-go/model-a', 'opencode-go/model-b']
        evidence = {
            'opencode-go/model-a': [{'title': '', 'snippet': 'fast lightweight'}],
            'opencode-go/model-b': [{'title': 'AIME math reasoning', 'snippet': 'SWE-bench competition'}],
        }
        result = _rank_models(models, evidence)
        assert result['opus'] == 'opencode-go/model-b'

    def test_haiku_absent_when_only_two_models(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']
        evidence = {
            'opencode-go/kimi-k2.5': [{'title': 'AIME', 'snippet': 'reasoning'}],
            'opencode-go/minimax-m2.7': [{'title': 'IFEval', 'snippet': 'instruction follow'}],
        }
        result = _rank_models(models, evidence)
        assert 'opus' in result
        assert 'sonnet' in result
        assert 'haiku' not in result


class TestKeyFinding:
    def test_returns_dim_markup_when_no_results(self) -> None:
        assert _key_finding([]) == '[dim]no recent data[/dim]'

    def test_truncates_long_snippets(self) -> None:
        results = [{'snippet': 'a' * 100, 'title': 'T', 'published': '', 'url': ''}]
        finding = _key_finding(results)
        assert finding.endswith('...')
        assert len(finding) == 63

    def test_returns_snippet_when_short(self) -> None:
        results = [{'snippet': 'Short snippet', 'title': 'T', 'published': '', 'url': ''}]
        assert _key_finding(results) == 'Short snippet'

    def test_falls_back_to_title_when_snippet_empty(self) -> None:
        results = [{'snippet': '   ', 'title': 'Model Benchmark Title', 'published': '', 'url': ''}]
        assert 'Model Benchmark Title' in _key_finding(results)


class TestRunCommand:
    def test_returns_1_when_no_models_fetched(self) -> None:
        with patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=[]):
            result = fetch_models.run(Namespace(yes=True, exa_key=None))
        assert result == 1

    def test_accepts_mapping_with_yes_flag(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence', return_value={}),
            patch('src.cli.commands.fetch_models.save_global_models') as mock_save,
            patch('src.cli.commands.fetch_models._display_tier_table'),
        ):
            result = fetch_models.run(Namespace(yes=True, exa_key=None))

        assert result == 0
        mock_save.assert_called_once()

    def test_aborts_when_user_declines(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence', return_value={}),
            patch('src.cli.commands.fetch_models.save_global_models') as mock_save,
            patch('src.cli.commands.fetch_models._display_tier_table'),
            patch('src.cli.commands.fetch_models.console') as mock_console,
        ):
            mock_console.input.return_value = 'n'
            result = fetch_models.run(Namespace(yes=False, exa_key=None))

        assert result == 1
        mock_save.assert_not_called()

    def test_uses_exa_when_key_provided(self) -> None:
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence', return_value={}) as mock_exa,
            patch('src.cli.commands.fetch_models.save_global_models'),
            patch('src.cli.commands.fetch_models._display_tier_table'),
            patch('src.cli.commands.fetch_models._display_evidence_table'),
        ):
            fetch_models.run(Namespace(yes=True, exa_key='my-exa-key'))

        mock_exa.assert_called_once_with(models, 'my-exa-key')

    def test_skips_exa_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('EXA_API_KEY', raising=False)
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence') as mock_exa,
            patch('src.cli.commands.fetch_models.save_global_models'),
            patch('src.cli.commands.fetch_models._display_tier_table'),
        ):
            fetch_models.run(Namespace(yes=True, exa_key=None))

        mock_exa.assert_not_called()

    def test_reads_exa_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('EXA_API_KEY', 'env-key')
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence', return_value={}) as mock_exa,
            patch('src.cli.commands.fetch_models.save_global_models'),
            patch('src.cli.commands.fetch_models._display_tier_table'),
            patch('src.cli.commands.fetch_models._display_evidence_table'),
        ):
            fetch_models.run(Namespace(yes=True, exa_key=None))

        mock_exa.assert_called_once_with(models, 'env-key')

    def test_cli_arg_overrides_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('EXA_API_KEY', 'env-key')
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.fetch_models._fetch_go_plan_models', return_value=models),
            patch('src.cli.commands.fetch_models._fetch_benchmark_evidence', return_value={}) as mock_exa,
            patch('src.cli.commands.fetch_models.save_global_models'),
            patch('src.cli.commands.fetch_models._display_tier_table'),
            patch('src.cli.commands.fetch_models._display_evidence_table'),
        ):
            fetch_models.run(Namespace(yes=True, exa_key='cli-key'))

        mock_exa.assert_called_once_with(models, 'cli-key')
