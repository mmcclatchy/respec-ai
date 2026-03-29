import json
import subprocess
import urllib.error
from argparse import Namespace
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.cli.commands import opencode_sync
from src.cli.commands.opencode_sync import (
    _detect_provider,
    _find_aa_match,
    _list_models,
    _parse_rate_limits_table,
    _score_models_by_tier,
    _suggest_tiers,
)


class TestDetectProvider:
    def _make_result(self, stdout: str) -> MagicMock:
        result = MagicMock()
        result.stdout = stdout
        return result

    def test_returns_provider_from_opencode_output_with_ansi(self) -> None:
        stdout = '┌  Credentials \x1b[90m~/.local/share/opencode/auth.json\n│\n●  OpenCode Go \x1b[90mapi\n│\n└  1 credentials\n'
        with patch('subprocess.run', return_value=self._make_result(stdout)):
            assert _detect_provider() == 'opencode-go'

    def test_returns_provider_without_ansi(self) -> None:
        stdout = '┌  Credentials\n│\n●  OpenCode Go api\n│\n└  1 credentials\n'
        with patch('subprocess.run', return_value=self._make_result(stdout)):
            assert _detect_provider() == 'opencode-go'

    def test_returns_provider_for_zen_plan(self) -> None:
        stdout = '┌  Credentials\n│\n●  OpenCode Zen \x1b[90mapi\n│\n└  1 credentials\n'
        with patch('subprocess.run', return_value=self._make_result(stdout)):
            assert _detect_provider() == 'opencode-zen'

    def test_returns_empty_when_opencode_not_installed(self) -> None:
        with patch('subprocess.run', side_effect=FileNotFoundError):
            assert _detect_provider() == ''

    def test_returns_empty_on_timeout(self) -> None:
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('opencode', 10)):
            assert _detect_provider() == ''


class TestListModels:
    def _make_result(self, stdout: str) -> MagicMock:
        result = MagicMock()
        result.stdout = stdout
        return result

    def test_returns_model_ids(self) -> None:
        stdout = 'opencode-go/glm-5\nopencode-go/kimi-k2.5\nopencode-go/minimax-m2.5\n'
        with patch('subprocess.run', return_value=self._make_result(stdout)):
            result = _list_models('opencode-go')
        assert result == ['opencode-go/glm-5', 'opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.5']

    def test_filters_lines_without_slash(self) -> None:
        stdout = 'Some header\nopencode-go/kimi-k2.5\n'
        with patch('subprocess.run', return_value=self._make_result(stdout)):
            result = _list_models('opencode-go')
        assert result == ['opencode-go/kimi-k2.5']

    def test_returns_empty_on_error(self) -> None:
        with patch('subprocess.run', side_effect=FileNotFoundError):
            assert _list_models('opencode-go') == []


class TestFindAaMatch:
    def test_exact_match(self) -> None:
        aa_data = {'kimi k2.5': {'artificial_analysis_coding_index': 80.0}}
        assert _find_aa_match('kimi-k2.5', aa_data) == 'kimi k2.5'

    def test_matches_reasoning_variant(self) -> None:
        aa_data = {
            'glm-5 (reasoning)': {'artificial_analysis_coding_index': 90.0},
            'glm-5 (non-reasoning)': {'artificial_analysis_coding_index': 50.0},
            'glm-5-turbo': {'artificial_analysis_coding_index': 70.0},
        }
        assert _find_aa_match('glm-5', aa_data) == 'glm-5 (reasoning)'

    def test_rejects_substring_false_positive(self) -> None:
        aa_data = {
            'minimax-m2': {'artificial_analysis_coding_index': 30.0},
            'minimax-m2.5': {'artificial_analysis_coding_index': 80.0},
        }
        assert _find_aa_match('minimax-m2.5', aa_data) == 'minimax-m2.5'

    def test_returns_empty_when_no_match(self) -> None:
        aa_data = {'gpt-4o': {'artificial_analysis_coding_index': 80.0}}
        assert _find_aa_match('kimi-k2.5', aa_data) == ''


class TestScoreModelsByTier:
    def _aa_data(self) -> dict[str, dict[str, float]]:
        return {
            'glm 5 (reasoning)': {
                'artificial_analysis_intelligence_index': 95.0,
            },
            'minimax-m2.7': {
                'artificial_analysis_intelligence_index': 80.0,
            },
        }

    def _rate_limits(self) -> dict[str, str]:
        return {
            'opencode-go/glm-5': '1,150',
            'opencode-go/minimax-m2.7': '14,000',
        }

    def test_reasoning_uses_intelligence_index(self) -> None:
        models = ['opencode-go/glm-5', 'opencode-go/minimax-m2.7']
        result = _score_models_by_tier(models, self._aa_data())
        assert result['reasoning'][0][0] == 'opencode-go/glm-5'
        assert result['reasoning'][0][1] == pytest.approx(95.0)

    def test_task_uses_throughput(self) -> None:
        models = ['opencode-go/glm-5', 'opencode-go/minimax-m2.7']
        result = _score_models_by_tier(models, self._aa_data(), rate_limits=self._rate_limits())
        assert result['task'][0][0] == 'opencode-go/minimax-m2.7'
        assert result['task'][0][1] == pytest.approx(14000.0)

    def test_different_top_models_per_tier(self) -> None:
        models = ['opencode-go/glm-5', 'opencode-go/minimax-m2.7']
        result = _score_models_by_tier(models, self._aa_data(), rate_limits=self._rate_limits())
        assert result['reasoning'][0][0] == 'opencode-go/glm-5'
        assert result['task'][0][0] == 'opencode-go/minimax-m2.7'

    def test_task_zero_without_rate_limits(self) -> None:
        models = ['opencode-go/glm-5']
        result = _score_models_by_tier(models, self._aa_data())
        assert result['task'][0][1] == 0.0

    def test_zero_reasoning_when_no_aa_data(self) -> None:
        models = ['opencode-go/unknown']
        result = _score_models_by_tier(models, {})
        assert result['reasoning'][0][1] == 0.0

    def test_returns_sorted_descending(self) -> None:
        models = ['opencode-go/minimax-m2.7', 'opencode-go/glm-5']
        result = _score_models_by_tier(models, self._aa_data(), rate_limits=self._rate_limits())
        reasoning_scores = [s for _, s in result['reasoning']]
        task_scores = [s for _, s in result['task']]
        assert reasoning_scores == sorted(reasoning_scores, reverse=True)
        assert task_scores == sorted(task_scores, reverse=True)


class TestSuggestTiers:
    def test_picks_top_from_each_tier(self) -> None:
        scored = {
            'reasoning': [('opencode-go/glm-5', 95.0), ('opencode-go/minimax-m2.7', 80.0)],
            'task': [('opencode-go/minimax-m2.7', 14000.0), ('opencode-go/glm-5', 1150.0)],
        }
        result = _suggest_tiers(scored)
        assert result['reasoning'] == 'opencode-go/glm-5'
        assert result['task'] == 'opencode-go/minimax-m2.7'

    def test_falls_back_to_second_reasoning_when_no_throughput(self) -> None:
        scored = {
            'reasoning': [('opencode-go/glm-5', 95.0), ('opencode-go/minimax-m2.7', 80.0)],
            'task': [('opencode-go/glm-5', 0.0), ('opencode-go/minimax-m2.7', 0.0)],
        }
        result = _suggest_tiers(scored)
        assert result['reasoning'] == 'opencode-go/glm-5'
        assert result['task'] == 'opencode-go/minimax-m2.7'

    def test_single_model_assigned_to_both(self) -> None:
        scored = {
            'reasoning': [('opencode-go/glm-5', 95.0)],
            'task': [('opencode-go/glm-5', 0.0)],
        }
        result = _suggest_tiers(scored)
        assert result['reasoning'] == 'opencode-go/glm-5'
        assert result['task'] == 'opencode-go/glm-5'

    def test_empty_scored_returns_empty(self) -> None:
        assert _suggest_tiers({'reasoning': [], 'task': []}) == {}


class TestParseRateLimitsTable:
    def test_parses_markdown_table(self) -> None:
        text = (
            '## Usage limits\n\n'
            '| | GLM-5 | Kimi K2.5 | MiniMax M2.7 | MiniMax M2.5 |\n'
            '| --- | --- | --- | --- | --- |\n'
            '| requests per 5 hour | 1,150 | 1,850 | 14,000 | 20,000 |\n'
            '| requests per week | 2,880 | 4,630 | 35,000 | 50,000 |\n'
        )
        result = _parse_rate_limits_table(text, 'opencode-go')
        assert result['opencode-go/glm-5'] == '1,150'
        assert result['opencode-go/kimi-k2.5'] == '1,850'
        assert result['opencode-go/minimax-m2.7'] == '14,000'
        assert result['opencode-go/minimax-m2.5'] == '20,000'

    def test_returns_empty_when_no_table(self) -> None:
        assert _parse_rate_limits_table('No table here', 'opencode-go') == {}

    def test_returns_empty_when_no_5_hour_row(self) -> None:
        text = '| | GLM-5 |\n| --- | --- |\n| requests per week | 2,880 |\n'
        assert _parse_rate_limits_table(text, 'opencode-go') == {}


class TestFetchRateLimits:
    @pytest.fixture(autouse=True)
    def _bypass_cache(self) -> Generator[None, None, None]:
        with patch('src.cli.commands.opencode_sync._read_cache', return_value=None):
            yield

    def _mock_exa(self, text: str) -> MagicMock:
        mock_result = MagicMock()
        mock_result.text = text
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.get_contents.return_value = mock_response
        return mock_client

    def test_fetches_and_parses_exa_response(self) -> None:
        text = '| | GLM-5 | Kimi K2.5 |\n| --- | --- | --- |\n| requests per 5 hour | 1,150 | 1,850 |\n'
        mock_client = self._mock_exa(text)
        with patch('src.cli.commands.opencode_sync.Exa', return_value=mock_client):
            result = opencode_sync._fetch_rate_limits('test-key', 'opencode-go')
        assert result['opencode-go/glm-5'] == '1,150'
        assert result['opencode-go/kimi-k2.5'] == '1,850'

    def test_returns_empty_on_error(self) -> None:
        with patch('src.cli.commands.opencode_sync.Exa', side_effect=Exception('connection failed')):
            result = opencode_sync._fetch_rate_limits('test-key', 'opencode-go')
        assert result == {}

    def test_returns_empty_when_no_results(self) -> None:
        mock_client = MagicMock()
        mock_client.get_contents.return_value = MagicMock(results=[])
        with patch('src.cli.commands.opencode_sync.Exa', return_value=mock_client):
            result = opencode_sync._fetch_rate_limits('test-key', 'opencode-go')
        assert result == {}


class TestFetchAaData:
    @pytest.fixture(autouse=True)
    def _bypass_cache(self) -> Generator[None, None, None]:
        with patch('src.cli.commands.opencode_sync._read_cache', return_value=None):
            yield

    def _make_resp(self, data: object) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(data).encode('utf-8')
        return mock_resp

    def test_parses_list_response_with_evaluations(self) -> None:
        data = [
            {
                'name': 'Kimi K2.5',
                'evaluations': {
                    'artificial_analysis_intelligence_index': 75.0,
                },
            },
        ]
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert 'kimi k2.5' in result
        assert result['kimi k2.5']['artificial_analysis_intelligence_index'] == pytest.approx(75.0)

    def test_parses_dict_response_with_models_key(self) -> None:
        data = {
            'models': [
                {
                    'name': 'Kimi K2.5',
                    'evaluations': {'artificial_analysis_intelligence_index': 90.0},
                },
            ],
        }
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert 'kimi k2.5' in result

    def test_uses_slug_when_name_missing(self) -> None:
        data = [{'slug': 'kimi-k2-5', 'evaluations': {'artificial_analysis_intelligence_index': 80.0}}]
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert 'kimi-k2-5' in result

    def test_returns_empty_on_network_error(self) -> None:
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('err')):
            result = opencode_sync._fetch_aa_data('test-key')
        assert result == {}

    def test_skips_models_without_scores(self) -> None:
        data = [{'name': 'Some Model', 'evaluations': {}}]
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert result == {}


class TestInteractiveOverride:
    def _scored(self) -> dict[str, list[tuple[str, float]]]:
        return {
            'reasoning': [('opencode-go/glm-5', 90.0), ('opencode-go/minimax-m2.7', 80.0)],
            'task': [('opencode-go/minimax-m2.7', 87.0), ('opencode-go/glm-5', 80.0)],
        }

    def _suggestion(self) -> dict[str, str]:
        return {'reasoning': 'opencode-go/glm-5', 'task': 'opencode-go/minimax-m2.7'}

    def test_number_selects_model(self) -> None:
        with patch.object(opencode_sync.console, 'input', side_effect=['1', '2', 'y']):
            with patch.object(opencode_sync.console, 'print'):
                result = opencode_sync._interactive_override(self._suggestion(), self._scored())
        assert result == {'reasoning': 'opencode-go/glm-5', 'task': 'opencode-go/glm-5'}

    def test_invalid_number_reprompts(self) -> None:
        with patch.object(opencode_sync.console, 'input', side_effect=['99', '1', '1', 'y']):
            with patch.object(opencode_sync.console, 'print'):
                result = opencode_sync._interactive_override(self._suggestion(), self._scored())
        assert result is not None
        assert result['reasoning'] == 'opencode-go/glm-5'

    def test_n_cancels_mapping(self) -> None:
        with patch.object(opencode_sync.console, 'input', side_effect=['1', '1', 'n']):
            with patch.object(opencode_sync.console, 'print'):
                result = opencode_sync._interactive_override(self._suggestion(), self._scored())
        assert result is None

    def test_empty_input_reprompts(self) -> None:
        with patch.object(opencode_sync.console, 'input', side_effect=['', '1', '1', 'y']):
            with patch.object(opencode_sync.console, 'print'):
                result = opencode_sync._interactive_override(self._suggestion(), self._scored())
        assert result is not None

    def test_non_digit_reprompts(self) -> None:
        with patch.object(opencode_sync.console, 'input', side_effect=['abc', '1', '1', 'y']):
            with patch.object(opencode_sync.console, 'print'):
                result = opencode_sync._interactive_override(self._suggestion(), self._scored())
        assert result is not None


class TestRunCommand:
    def test_returns_1_when_no_models_found(self) -> None:
        with patch('src.cli.commands.opencode_sync._discover_models', return_value=('', [])):
            result = opencode_sync.run(Namespace(yes=True, aa_key=None, exa_key=None, debug=False, no_cache=True))
        assert result == 1

    def test_saves_mapping_with_yes_flag(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data', return_value={}),
            patch('src.cli.commands.opencode_sync.save_global_models') as mock_save,
        ):
            result = opencode_sync.run(Namespace(yes=True, aa_key=None, exa_key=None, debug=False, no_cache=True))
        assert result == 0
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert 'reasoning' in saved
        assert 'task' in saved

    def test_uses_aa_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('ARTIFICIAL_ANALYSIS_API_KEY', 'env-key')
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data', return_value={}) as mock_aa,
            patch('src.cli.commands.opencode_sync.save_global_models'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key=None, exa_key=None, debug=False, no_cache=True))
        mock_aa.assert_called_once_with('env-key', debug=False)

    def test_cli_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('ARTIFICIAL_ANALYSIS_API_KEY', 'env-key')
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data', return_value={}) as mock_aa,
            patch('src.cli.commands.opencode_sync.save_global_models'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key='cli-key', exa_key=None, debug=False, no_cache=True))
        mock_aa.assert_called_once_with('cli-key', debug=False)

    def test_skips_aa_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data') as mock_aa,
            patch('src.cli.commands.opencode_sync.save_global_models'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key=None, exa_key=None, debug=False, no_cache=True))
        mock_aa.assert_not_called()

    def test_fetches_rate_limits_when_exa_key_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)
        monkeypatch.delenv('EXA_API_KEY', raising=False)
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data') as mock_aa,
            patch('src.cli.commands.opencode_sync._fetch_rate_limits', return_value={}) as mock_rl,
            patch('src.cli.commands.opencode_sync.save_global_models'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key=None, exa_key='exa-test', debug=False, no_cache=True))
        mock_aa.assert_not_called()
        mock_rl.assert_called_once_with('exa-test', 'opencode-go', debug=False)
