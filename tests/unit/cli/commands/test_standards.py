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

    def test_parses_render_subcommand(self) -> None:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['render'])
        assert args.standards_command == 'render'


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

    def test_render_fails_on_invalid_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai' / 'config'
        standards_dir = config_dir / 'standards'
        standards_dir.mkdir(parents=True)
        (config_dir / 'stack.toml').write_text('schema_version = 1\n[project]\nlanguage = "python"\nlanguages=["python"]\n')
        (standards_dir / 'python.toml').write_text('schema_version = 1\nlanguage = "python"\n')

        parser = ArgumentParser()
        standards.add_arguments(parser)
        args = parser.parse_args(['render'])

        result = standards.run(args)

        assert result == 1
