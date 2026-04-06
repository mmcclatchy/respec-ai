from argparse import ArgumentParser, Namespace
from unittest.mock import patch

import pytest

from src.cli.commands import models


class TestModelsArguments:
    def test_requires_subcommand(self) -> None:
        parser = ArgumentParser()
        models.add_arguments(parser)
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parses_opencode_subcommand(self) -> None:
        parser = ArgumentParser()
        models.add_arguments(parser)
        args = parser.parse_args(['opencode', '--yes'])
        assert args.models_command == 'opencode'
        assert args.yes is True

    def test_parses_codex_subcommand(self) -> None:
        parser = ArgumentParser()
        models.add_arguments(parser)
        args = parser.parse_args(['codex', '--yes'])
        assert args.models_command == 'codex'
        assert args.yes is True


class TestModelsRun:
    def test_dispatches_opencode(self) -> None:
        with patch('src.cli.commands.models.opencode_model.run', return_value=0) as mock_run:
            result = models.run(Namespace(models_command='opencode'))
        assert result == 0
        mock_run.assert_called_once()

    def test_dispatches_codex(self) -> None:
        with patch('src.cli.commands.models.codex_model.run', return_value=0) as mock_run:
            result = models.run(Namespace(models_command='codex'))
        assert result == 0
        mock_run.assert_called_once()

    def test_returns_error_for_unknown_subcommand(self) -> None:
        result = models.run(Namespace(models_command='unknown'))
        assert result == 1
