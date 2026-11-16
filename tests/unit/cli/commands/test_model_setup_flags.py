from argparse import ArgumentParser
from collections.abc import Callable

import pytest

from src.cli.commands import init, models, sync


PARSER_CASES: list[tuple[Callable[[ArgumentParser], None], list[str]]] = [
    (init.add_arguments, []),
    (sync.add_arguments, []),
    (models.add_arguments, ['opencode']),
]
PARSER_CASE_IDS = ['init', 'sync', 'models-opencode']
REMOVED_FLAG = '--exa-key'


@pytest.mark.parametrize(('add_arguments', 'prefix'), PARSER_CASES, ids=PARSER_CASE_IDS)
def test_rejects_removed_exa_flag(
    add_arguments: Callable[[ArgumentParser], None],
    prefix: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = ArgumentParser()
    add_arguments(parser)

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([*prefix, REMOVED_FLAG, 'value'])

    assert exc_info.value.code == 2
    assert f'unrecognized arguments: {REMOVED_FLAG}' in capsys.readouterr().err


@pytest.mark.parametrize(('add_arguments', 'prefix'), PARSER_CASES, ids=PARSER_CASE_IDS)
def test_accepts_aa_key_override(add_arguments: Callable[[ArgumentParser], None], prefix: list[str]) -> None:
    parser = ArgumentParser()
    add_arguments(parser)

    args = parser.parse_args([*prefix, '--aa-key', 'one-run-key'])

    assert args.aa_key == 'one-run-key'
