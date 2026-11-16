import io
import json
from argparse import Namespace
from pathlib import Path

import pytest

from src.cli.commands import check_conformance


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


class TestCheckConformanceCommand:
    def test_reports_a_blocker_for_a_missing_designed_member(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path / 'src/kb/client.py', 'class Client:\n    def __init__(self) -> None:\n        pass\n')
        payload = {
            'skeleton_index_text': '- `src/kb/client.py` :: Client.query(cypher: str) -> list[dict]',
            'deviations': [],
        }
        monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(payload)))

        exit_code = check_conformance.run(Namespace(project_root=str(tmp_path)))

        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output['blockers'] == [
            {'qualified_name': 'Client.query', 'kind': 'missing', 'detail': 'designed member never implemented'}
        ]
        assert output['findings'] == []

    def test_recorded_deviation_updates_the_returned_skeleton_index(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Client:\n    def query(self, cypher: str, limit: int) -> list[dict]:\n        raise NotImplementedError\n',
        )
        payload = {
            'skeleton_index_text': '- `src/kb/client.py` :: Client.query(cypher: str) -> list[dict]',
            'deviations': [{'qualified_name': 'Client.query', 'reason': 'needed a limit'}],
        }
        monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(payload)))

        exit_code = check_conformance.run(Namespace(project_root=str(tmp_path)))

        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output['blockers'] == []
        assert 'limit: int' in output['updated_skeleton_index']
        assert 'needed a limit' in output['new_settled_decisions']

    @pytest.mark.parametrize(
        ('path', 'native_signature'),
        [
            ('src/loader.py', 'def load(paths: list[str]) -> dict[str, int]:'),
            ('internal/loader/loader.go', 'func Load(paths []string) map[string]int'),
            ('Sources/App/Router.swift', 'Router.register(_:on:)'),
        ],
        ids=['language-with-materializer', 'language-without-materializer', 'text-rich-reads-as-an-emoji-code'],
    )
    def test_a_native_declaration_in_the_skeleton_index_is_one_readable_error_quoting_the_entry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        path: str,
        native_signature: str,
    ) -> None:
        payload = {'skeleton_index_text': f'- `{path}` :: {native_signature}', 'deviations': []}
        monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(payload)))

        exit_code = check_conformance.run(Namespace(project_root=str(tmp_path)))

        captured = capsys.readouterr()
        output = ' '.join(captured.out.split())
        assert exit_code == 1
        assert path in output
        assert native_signature in output
        assert 'Traceback' not in captured.out + captured.err
