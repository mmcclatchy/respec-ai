from argparse import Namespace

from pytest_mock import MockerFixture

from src.cli.services.tui_model_setup import run_tui_model_setup
from src.platform.tui_selector import TuiType


def test_claude_code_skips_model_setup(mocker: MockerFixture) -> None:
    mock_codex = mocker.patch('src.cli.services.tui_model_setup.codex_model.run')
    mock_opencode = mocker.patch('src.cli.services.tui_model_setup.opencode_model.run')

    result = run_tui_model_setup(TuiType.CLAUDE_CODE, Namespace())

    assert result == 0
    mock_codex.assert_not_called()
    mock_opencode.assert_not_called()


def test_codex_runs_model_setup_command(mocker: MockerFixture) -> None:
    mock_run = mocker.patch('src.cli.services.tui_model_setup.codex_model.run', return_value=0)

    args = Namespace(aa_key='aa-key', yes=True)
    result = run_tui_model_setup(TuiType.CODEX, args)

    assert result == 0
    mock_run.assert_called_once()
    passed = mock_run.call_args.args[0]
    assert passed.aa_key == 'aa-key'
    assert passed.yes is True
    assert passed.debug is False
    assert passed.no_cache is False
    assert passed.reasoning_model is None
    assert passed.task_model is None


def test_opencode_runs_model_setup_command(mocker: MockerFixture) -> None:
    mock_run = mocker.patch('src.cli.services.tui_model_setup.opencode_model.run', return_value=0)

    args = Namespace(aa_key='aa-key', exa_key='exa-key', yes=False)
    result = run_tui_model_setup(TuiType.OPENCODE, args)

    assert result == 0
    mock_run.assert_called_once()
    passed = mock_run.call_args.args[0]
    assert passed.aa_key == 'aa-key'
    assert passed.exa_key == 'exa-key'
    assert passed.yes is False
    assert passed.debug is False
    assert passed.no_cache is False
