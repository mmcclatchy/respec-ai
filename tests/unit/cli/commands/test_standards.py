from argparse import ArgumentParser
from pathlib import Path

import pytest

from src.cli.commands import standards


class TestStandardsArgumentParsing:
    def test_parses_init_subcommand(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', 'python', 'typescript'])
        assert args.standards_command == 'init'
        assert args.languages == ['python', 'typescript']

    def test_parses_validate_subcommand(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['validate'])
        assert args.standards_command == 'validate'

    def test_init_requires_at_least_one_language(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(['init'])


class TestStandardsCommandExecution:
    def test_init_writes_requested_language_files_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', 'python', 'typescript'])

        result = standards.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config' / 'standards' / 'python.toml').exists()
        assert (tmp_path / '.respec-ai' / 'config' / 'standards' / 'typescript.toml').exists()
        assert not (tmp_path / '.respec-ai' / 'config' / 'standards' / 'java.toml').exists()

    def test_init_fails_all_when_any_language_is_unsupported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', 'python', 'not-a-language'])

        result = standards.run(args)

        assert result == 1
        assert not (tmp_path / '.respec-ai' / 'config' / 'standards' / 'python.toml').exists()

    def test_init_generates_defaults_not_blank(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['init', 'python'])

        result = standards.run(args)

        assert result == 0
        generated = (tmp_path / '.respec-ai' / 'config' / 'standards' / 'python.toml').read_text(encoding='utf-8')
        assert 'test = ""' not in generated
        assert 'naming = []' not in generated

    def test_validate_fails_when_config_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['validate'])

        result = standards.run(args)

        assert result == 1
