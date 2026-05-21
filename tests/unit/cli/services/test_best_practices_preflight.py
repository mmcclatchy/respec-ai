from pytest_mock import MockerFixture

from src.cli.services.best_practices_preflight import ensure_best_practices_ready


def test_preflight_normalizes_claude_code_tui(mocker: MockerFixture) -> None:
    mocker.patch('src.cli.services.best_practices_preflight.shutil.which', return_value='/usr/bin/best-practices-rag')
    run = mocker.patch('src.cli.services.best_practices_preflight._run', return_value=True)

    result = ensure_best_practices_ready(tui='claude-code', yes=True, skip_setup=False)

    assert result is True
    run.assert_called_once_with(['best-practices-rag', 'check', '--tui', 'claude'])


def test_preflight_setup_flow_uses_normalized_tui(mocker: MockerFixture) -> None:
    mocker.patch('src.cli.services.best_practices_preflight.shutil.which', return_value='/usr/bin/best-practices-rag')
    run = mocker.patch(
        'src.cli.services.best_practices_preflight._run',
        side_effect=[False, True, True],
    )

    result = ensure_best_practices_ready(tui='claude-code', yes=True, skip_setup=False)

    assert result is True
    assert run.call_args_list[0].args[0] == ['best-practices-rag', 'check', '--tui', 'claude']
    assert run.call_args_list[1].args[0] == ['best-practices-rag', 'setup', '--tui', 'claude']
    assert run.call_args_list[2].args[0] == ['best-practices-rag', 'check', '--tui', 'claude']
