import json
from argparse import Namespace
from pathlib import Path

import pytest

from src.cli.commands import materialize_skeletons


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


class TestMaterializeSkeletonsCommand:
    def test_writes_skeletons_and_tests_under_the_current_working_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        index_file = _write(
            tmp_path / 'index.md', '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        test_file = _write(
            tmp_path / 'tests.md', '- `tests/unit/test_client.py::test_query_returns_a_list`\n'
        )

        exit_code = materialize_skeletons.run(
            Namespace(skeleton_index_file=str(index_file), test_list_file=str(test_file), merge_paths='')
        )

        assert exit_code == 0
        assert (tmp_path / 'src' / 'kb' / 'client.py').exists()
        assert (tmp_path / 'tests' / 'unit' / 'test_client.py').exists()

        output = json.loads(capsys.readouterr().out)
        assert output['written_skeletons'] == ['src/kb/client.py']
        assert output['written_tests'] == ['tests/unit/test_client.py']
        assert output['reconciliation_needed'] == []

    def test_reports_reconciliation_needed_for_an_existing_source_file_without_overwriting_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        original = 'class Client:\n    def query(self) -> list[str]:\n        return []\n'
        _write(tmp_path / 'src' / 'kb' / 'client.py', original)
        index_file = _write(
            tmp_path / 'index.md', '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        test_file = _write(tmp_path / 'tests.md', '')

        exit_code = materialize_skeletons.run(
            Namespace(skeleton_index_file=str(index_file), test_list_file=str(test_file), merge_paths='')
        )

        assert exit_code == 0
        assert (tmp_path / 'src' / 'kb' / 'client.py').read_text() == original

        output = json.loads(capsys.readouterr().out)
        assert output['written_skeletons'] == []
        assert output['reconciliation_needed'] == [
            {
                'path': 'src/kb/client.py',
                'existing_signatures': ['Client.query() -> list[str]'],
                'designed_signatures': ['Client.query(cypher: str) -> list[str]'],
            }
        ]

    def test_merge_paths_appends_only_new_members_and_clears_that_path_from_reconciliation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        original = 'class Client:\n    def query(self) -> list[str]:\n        return []\n'
        _write(tmp_path / 'src' / 'kb' / 'client.py', original)
        index_file = _write(
            tmp_path / 'index.md',
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
            '- `src/kb/client.py` :: Client.close() -> None\n',
        )
        test_file = _write(tmp_path / 'tests.md', '')

        exit_code = materialize_skeletons.run(
            Namespace(
                skeleton_index_file=str(index_file),
                test_list_file=str(test_file),
                merge_paths='src/kb/client.py',
            )
        )

        assert exit_code == 0
        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'return []' in content
        assert 'def close(self) -> None:' in content

        output = json.loads(capsys.readouterr().out)
        assert output['merged_paths'] == ['src/kb/client.py']
        assert output['reconciliation_needed'] == []
        # `query` was designed with a different signature than what's on disk (existing
        # has no `cypher` param) -- B2: that's an unresolved conflict, not a silent
        # no-op. `close` is genuinely new and gets appended regardless.
        assert output['unresolved_signature_conflicts'] == ['Client.query(cypher: str) -> list[str]']

    def test_merge_reports_a_divergent_same_name_member_as_unresolved_without_touching_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        original = 'class Client:\n    def query(self) -> list[str]:\n        return []\n'
        _write(tmp_path / 'src' / 'kb' / 'client.py', original)
        index_file = _write(
            tmp_path / 'index.md', '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        test_file = _write(tmp_path / 'tests.md', '')

        exit_code = materialize_skeletons.run(
            Namespace(
                skeleton_index_file=str(index_file),
                test_list_file=str(test_file),
                merge_paths='src/kb/client.py',
            )
        )

        assert exit_code == 0
        assert (tmp_path / 'src' / 'kb' / 'client.py').read_text() == original

        output = json.loads(capsys.readouterr().out)
        assert output['merged_paths'] == []
        assert output['unresolved_signature_conflicts'] == ['Client.query(cypher: str) -> list[str]']

    def test_a_skeleton_index_entry_escaping_the_project_root_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        index_file = _write(tmp_path / 'index.md', '- `../../etc/evil.py` :: Evil.run() -> None\n')
        test_file = _write(tmp_path / 'tests.md', '')

        exit_code = materialize_skeletons.run(
            Namespace(skeleton_index_file=str(index_file), test_list_file=str(test_file), merge_paths='')
        )

        assert exit_code == 1
        assert not (tmp_path.parent.parent / 'etc' / 'evil.py').exists()
