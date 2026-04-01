from argparse import ArgumentParser, Namespace
from pathlib import Path

import pytest

from src.cli.commands import standards


class TestStandardsArgumentParsing:
    @pytest.fixture
    def parser(self) -> ArgumentParser:
        parser = ArgumentParser()
        standards.add_arguments(parser)
        return parser

    def test_upgrade_flag(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['--upgrade'])
        assert args.upgrade is True
        assert args.language is None

    def test_upgrade_with_language(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['--upgrade', 'python'])
        assert args.upgrade is True
        assert args.language == 'python'

    def test_no_flags(self, parser: ArgumentParser) -> None:
        args = parser.parse_args([])
        assert args.upgrade is False


class TestStandardsRunCommand:
    def test_requires_upgrade_flag(self) -> None:
        args = Namespace(upgrade=False, language=None)
        result = standards.run(args)
        assert result == 1

    def test_upgrade_missing_config_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        args = Namespace(upgrade=True, language=None)
        result = standards.run(args)
        assert result == 1

    def test_upgrade_upgrades_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)
        (config_dir / 'python.md').write_text('## Coding Standards\n\n### Naming\n- snake_case\n')

        args = Namespace(upgrade=True, language=None)
        result = standards.run(args)

        assert result == 0
        content = (config_dir / 'python.md').read_text()
        assert 'MANDATORY' in content

    def test_upgrade_specific_language(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)
        (config_dir / 'python.md').write_text('## Coding Standards\n\n### Naming\n- snake_case\n')
        (config_dir / 'javascript.md').write_text('## Coding Standards\n\n### Naming\n- camelCase\n')

        args = Namespace(upgrade=True, language='python')
        result = standards.run(args)

        assert result == 0
        python_content = (config_dir / 'python.md').read_text()
        js_content = (config_dir / 'javascript.md').read_text()
        assert 'MANDATORY' in python_content
        assert 'MANDATORY' not in js_content

    def test_upgrade_nonexistent_language(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)

        args = Namespace(upgrade=True, language='rust')
        result = standards.run(args)

        assert result == 1
