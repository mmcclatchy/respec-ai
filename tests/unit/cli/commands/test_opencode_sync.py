import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from src.cli.commands import opencode_sync
from src.cli.commands.opencode_sync import (
    _detect_provider,
    _find_aa_match,
    _list_models,
    _score_models,
    _suggest_tiers,
)


import subprocess
import urllib.error


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
    def test_matches_substring(self) -> None:
        aa_data = {'kimi-k2.5': {'coding_index': 80.0}}
        assert _find_aa_match('kimi-k2.5', aa_data) == 'kimi-k2.5'

    def test_matches_partial(self) -> None:
        aa_data = {'kimi k2.5 model': {'coding_index': 80.0}}
        assert _find_aa_match('kimi', aa_data) == 'kimi k2.5 model'

    def test_returns_empty_when_no_match(self) -> None:
        aa_data = {'gpt-4o': {'coding_index': 80.0}}
        assert _find_aa_match('kimi-k2.5', aa_data) == ''


class TestScoreModels:
    def test_sums_quality_fields(self) -> None:
        models = ['opencode-go/kimi-k2.5']
        aa_data = {'kimi-k2.5': {'coding_index': 80.0, 'reasoning_index': 75.0, 'math_index': 70.0}}
        scored = _score_models(models, aa_data)
        assert scored[0][0] == 'opencode-go/kimi-k2.5'
        assert scored[0][1] == pytest.approx(225.0)

    def test_zero_score_when_no_aa_data(self) -> None:
        models = ['opencode-go/unknown-model']
        scored = _score_models(models, {})
        assert scored[0][1] == 0.0

    def test_returns_sorted_descending(self) -> None:
        models = ['opencode-go/model-a', 'opencode-go/model-b']
        aa_data = {
            'model-a': {'coding_index': 50.0},
            'model-b': {'coding_index': 90.0},
        }
        scored = _score_models(models, aa_data)
        assert scored[0][0] == 'opencode-go/model-b'
        assert scored[1][0] == 'opencode-go/model-a'


class TestSuggestTiers:
    def test_assigns_reasoning_to_top_model(self) -> None:
        scored = [('opencode-go/kimi-k2.5', 225.0), ('opencode-go/minimax-m2.7', 180.0)]
        result = _suggest_tiers(scored)
        assert result['reasoning'] == 'opencode-go/kimi-k2.5'
        assert result['task'] == 'opencode-go/minimax-m2.7'

    def test_single_model_assigned_to_both_tiers(self) -> None:
        scored = [('opencode-go/kimi-k2.5', 225.0)]
        result = _suggest_tiers(scored)
        assert result['reasoning'] == 'opencode-go/kimi-k2.5'
        assert result['task'] == 'opencode-go/kimi-k2.5'

    def test_empty_scored_returns_empty(self) -> None:
        assert _suggest_tiers([]) == {}


class TestFetchAaData:
    def _make_resp(self, data: object) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(data).encode('utf-8')
        return mock_resp

    def test_parses_list_response(self) -> None:
        data = [{'model_name': 'Kimi K2.5', 'coding_index': 80.0, 'reasoning_index': 75.0}]
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert 'kimi k2.5' in result
        assert result['kimi k2.5']['coding_index'] == pytest.approx(80.0)

    def test_parses_dict_response_with_models_key(self) -> None:
        data = {'models': [{'model_name': 'Kimi K2.5', 'intelligence_index': 90.0}]}
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert 'kimi k2.5' in result

    def test_returns_empty_on_network_error(self) -> None:
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('err')):
            result = opencode_sync._fetch_aa_data('test-key')
        assert result == {}

    def test_skips_models_without_scores(self) -> None:
        data = [{'model_name': 'Some Model'}]
        with patch('urllib.request.urlopen', return_value=self._make_resp(data)):
            result = opencode_sync._fetch_aa_data('test-key')
        assert result == {}


class TestRunCommand:
    def test_returns_1_when_no_models_found(self) -> None:
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('', [])),
        ):
            result = opencode_sync.run(Namespace(yes=True, aa_key=None))
        assert result == 1

    def test_saves_mapping_with_yes_flag(self) -> None:
        models = ['opencode-go/kimi-k2.5', 'opencode-go/minimax-m2.7']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data', return_value={}),
            patch('src.cli.commands.opencode_sync.save_global_models') as mock_save,
            patch('src.cli.commands.opencode_sync._display_suggestion_table'),
        ):
            result = opencode_sync.run(Namespace(yes=True, aa_key=None))
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
            patch('src.cli.commands.opencode_sync._display_suggestion_table'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key=None))
        mock_aa.assert_called_once_with('env-key')

    def test_cli_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('ARTIFICIAL_ANALYSIS_API_KEY', 'env-key')
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data', return_value={}) as mock_aa,
            patch('src.cli.commands.opencode_sync.save_global_models'),
            patch('src.cli.commands.opencode_sync._display_suggestion_table'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key='cli-key'))
        mock_aa.assert_called_once_with('cli-key')

    def test_skips_aa_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('ARTIFICIAL_ANALYSIS_API_KEY', raising=False)
        models = ['opencode-go/kimi-k2.5']
        with (
            patch('src.cli.commands.opencode_sync._discover_models', return_value=('opencode-go', models)),
            patch('src.cli.commands.opencode_sync._fetch_aa_data') as mock_aa,
            patch('src.cli.commands.opencode_sync.save_global_models'),
            patch('src.cli.commands.opencode_sync._display_suggestion_table'),
        ):
            opencode_sync.run(Namespace(yes=True, aa_key=None))
        mock_aa.assert_not_called()
