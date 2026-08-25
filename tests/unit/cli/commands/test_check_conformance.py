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
