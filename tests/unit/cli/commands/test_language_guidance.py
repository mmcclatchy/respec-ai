import os
import re
from argparse import Namespace
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.cli.commands import language_guidance
from src.cli.commands.language_guidance import NO_DECLARED_LANGUAGES_NOTE
from src.utils.materializers import UNMATERIALIZED_LANGUAGE_NOTE, PythonMaterializer, TypeScriptMaterializer


_SECTION_HEADING = re.compile(r'^#### (.+)$', re.MULTILINE)


def _write_stack_toml(project_root: Path, content: str | bytes) -> Path:
    stack_toml = project_root / '.respec-ai' / 'config' / 'stack.toml'
    stack_toml.parent.mkdir(parents=True, exist_ok=True)
    stack_toml.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
    return stack_toml


def _stack_toml_declaring(languages: str) -> str:
    return f'schema_version = 2\n\n[project]\nprimary_language = "python"\nlanguages = {languages}\n'


def _section_headings(output: str) -> list[str]:
    return _SECTION_HEADING.findall(output)


def _sections(output: str) -> dict[str, str]:
    parts = _SECTION_HEADING.split(output)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


@pytest.fixture
def untraversable_config_dir(tmp_path: Path) -> Iterator[Path]:
    if os.geteuid() == 0:
        pytest.skip('root traverses every directory regardless of its mode')
    config_dir = _write_stack_toml(tmp_path, _stack_toml_declaring('["python"]')).parent
    config_dir.chmod(0o000)
    yield config_dir
    config_dir.chmod(0o755)


def _normalized_output(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    return ' '.join((captured.out + captured.err).split())


class TestLanguageGuidanceCommand:
    def test_notes_cover_exactly_the_declared_languages_in_stack_toml_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_stack_toml(tmp_path, _stack_toml_declaring('["python", "go"]'))

        exit_code = language_guidance.run(Namespace())

        output = capsys.readouterr().out
        sections = _sections(output)
        assert exit_code == 0
        assert _section_headings(output) == ['python', 'go']
        assert PythonMaterializer.authoring_guidance in sections['python']
        assert UNMATERIALIZED_LANGUAGE_NOTE in sections['go']
        assert TypeScriptMaterializer.authoring_guidance not in output

    def test_a_language_declared_twice_or_in_another_case_gets_its_own_notes_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_stack_toml(tmp_path, _stack_toml_declaring('["TypeScript", "Go", "typescript"]'))

        exit_code = language_guidance.run(Namespace())

        output = capsys.readouterr().out
        assert exit_code == 0
        assert _section_headings(output) == ['typescript', 'go']
        assert TypeScriptMaterializer.authoring_guidance in _sections(output)['typescript']

    def test_a_project_with_no_stack_toml_gets_the_no_declared_languages_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)

        exit_code = language_guidance.run(Namespace())

        assert exit_code == 0
        assert NO_DECLARED_LANGUAGES_NOTE in capsys.readouterr().out

    def test_a_stack_toml_with_an_empty_language_list_gets_the_no_declared_languages_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_stack_toml(tmp_path, _stack_toml_declaring('[]'))

        exit_code = language_guidance.run(Namespace())

        assert exit_code == 0
        assert NO_DECLARED_LANGUAGES_NOTE in capsys.readouterr().out

    @pytest.mark.parametrize('unusable_stack_toml', ['malformed', 'unreadable', 'non_utf8'])
    def test_an_unusable_stack_toml_is_one_readable_error_naming_it(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        unusable_stack_toml: str,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        if unusable_stack_toml == 'malformed':
            _write_stack_toml(tmp_path, '[project\nlanguages = ["python"\n')
        elif unusable_stack_toml == 'non_utf8':
            _write_stack_toml(tmp_path, b'# caf\xe9\n[project]\nlanguages = ["python"]\n')
        else:
            (tmp_path / '.respec-ai' / 'config' / 'stack.toml').mkdir(parents=True)

        exit_code = language_guidance.run(Namespace())

        output = _normalized_output(capsys)
        assert exit_code == 1
        assert 'stack.toml' in output
        assert 'Traceback' not in output

    def test_a_stack_toml_behind_an_untraversable_directory_is_one_readable_error_naming_it(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        untraversable_config_dir: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        exit_code = language_guidance.run(Namespace())

        output = _normalized_output(capsys)
        assert exit_code == 1
        assert 'stack.toml' in output
        assert 'Traceback' not in output
