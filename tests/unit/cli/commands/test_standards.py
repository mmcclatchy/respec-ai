from argparse import ArgumentParser
from pathlib import Path

import pytest

from src.cli.commands import standards


class TestStandardsArgumentParsing:
    def test_parses_init_subcommand(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', '--language', 'python'])
        assert args.standards_command == 'init'
        assert args.language == 'python'

    def test_parses_validate_subcommand(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['validate'])
        assert args.standards_command == 'validate'


class TestStandardsCommandExecution:
    def test_init_writes_template(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', '--language', 'python'])

        result = standards.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config' / 'standards' / 'python.toml').exists()

    def test_validate_fails_when_config_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['validate'])

        result = standards.run(args)

        assert result == 1
