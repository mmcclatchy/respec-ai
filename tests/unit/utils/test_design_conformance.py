from pathlib import Path

from src.utils.design_conformance import RecordedDeviation, classify_conformance


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


class TestMissingDesignedMethodBlocks:
    def test_a_designed_public_method_that_was_never_implemented_blocks_the_review(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n    def __init__(self) -> None:\n        pass\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        report = classify_conformance(tmp_path, index_text)

        assert any(b.qualified_name == 'Neo4jClient.query' and b.kind == 'missing' for b in report.blockers)


class TestNewCrossModuleMethodBlocks:
    def test_a_new_public_method_crossing_a_module_boundary_blocks_the_review(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, cypher: str) -> list[dict]:\n'
            '        raise NotImplementedError\n\n'
            '    def close(self) -> None:\n'
            '        raise NotImplementedError\n',
        )
        _write(
            tmp_path / 'src/kb/consumer.py',
            'from src.kb.client import Neo4jClient\n\n'
            'def shutdown(client: Neo4jClient) -> None:\n'
            '    client.close()\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        report = classify_conformance(tmp_path, index_text)

        assert any(b.qualified_name == 'Neo4jClient.close' and b.kind == 'added_cross_module' for b in report.blockers)


class TestNewInternalMethodDoesNotBlock:
    def test_a_new_module_internal_method_does_not_block(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, cypher: str) -> list[dict]:\n'
            '        raise NotImplementedError\n\n'
            '    def reconnect(self) -> None:\n'
            '        raise NotImplementedError\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        report = classify_conformance(tmp_path, index_text)

        assert not any(b.qualified_name == 'Neo4jClient.reconnect' for b in report.blockers)
        assert any(f.qualified_name == 'Neo4jClient.reconnect' and f.kind == 'added_internal' for f in report.findings)


class TestUnrecordedProtocolChangeBlocks:
    def test_a_changed_protocol_without_a_recorded_reason_blocks(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, cypher: str, limit: int) -> list[dict]:\n'
            '        raise NotImplementedError\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        report = classify_conformance(tmp_path, index_text)

        assert any(
            b.qualified_name == 'Neo4jClient.query' and b.kind == 'protocol_changed_unrecorded' for b in report.blockers
        )


class TestRecordedProtocolChangePassesAndUpdatesRecord:
    def test_a_changed_protocol_with_a_recorded_reason_passes_and_the_design_record_is_updated_to_match(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, cypher: str, limit: int) -> list[dict]:\n'
            '        raise NotImplementedError\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'
        deviations = (RecordedDeviation('Neo4jClient.query', 'limit required to cap unbounded scans'),)

        report = classify_conformance(tmp_path, index_text, deviations)

        assert not any(b.qualified_name == 'Neo4jClient.query' for b in report.blockers)
        assert 'Neo4jClient.query(cypher: str, limit: int) -> list[dict]' in report.updated_skeleton_index
        assert 'limit required to cap unbounded scans' in report.new_settled_decisions


class TestCosmeticSignatureChangeDoesNotBlock:
    def test_a_cosmetic_signature_change_does_not_block(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, query_text: str) -> list[dict]:\n'
            '        raise NotImplementedError\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        report = classify_conformance(tmp_path, index_text)

        assert not any(b.qualified_name == 'Neo4jClient.query' for b in report.blockers)
        assert any(f.qualified_name == 'Neo4jClient.query' and f.kind == 'cosmetic_changed' for f in report.findings)


class TestWriteBackNeverTouchesModuleLayoutOrWiring:
    def test_write_back_only_returns_skeleton_index_and_settled_decision_fields(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.py',
            'class Neo4jClient:\n'
            '    def query(self, cypher: str, limit: int) -> list[dict]:\n'
            '        raise NotImplementedError\n',
        )
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'
        deviations = (RecordedDeviation('Neo4jClient.query', 'needed a limit'),)

        report = classify_conformance(tmp_path, index_text, deviations)

        report_fields = set(vars(report).keys())
        assert report_fields == {'blockers', 'findings', 'updated_skeleton_index', 'new_settled_decisions'}
