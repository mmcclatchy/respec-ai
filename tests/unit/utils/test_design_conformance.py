from pathlib import Path

from src.utils.design_conformance import (
    ConformanceParseError,
    RecordedDeviation,
    _is_referenced_from_another_module,
    _is_test_file,
    classify_conformance,
)
from src.utils.skeleton_generator import SkeletonMember, parse_skeleton_index


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


class TestTypeScriptTestFilesAreRecognizedAsTests:
    def test_a_spec_ts_file_is_a_test_file_not_a_production_module(self, tmp_path: Path) -> None:
        assert _is_test_file(tmp_path / 'src/kb/client.spec.ts')
        assert _is_test_file(tmp_path / 'src/kb/client.test.tsx')

    def test_a_plain_ts_file_is_not_a_test_file(self, tmp_path: Path) -> None:
        assert not _is_test_file(tmp_path / 'src/kb/client.ts')


class TestCrossModuleReferenceDetectionIsLanguageAware:
    def test_a_typescript_import_of_a_designed_export_is_detected_as_cross_module(self, tmp_path: Path) -> None:
        owning_path = tmp_path / 'src/kb/client.ts'
        _write(owning_path, "export class Client {\n  close(): void {}\n}\n")
        _write(
            tmp_path / 'src/kb/consumer.ts',
            "import { Client } from './client'\n\nfunction shutdown(c: Client): void {\n  c.close()\n}\n",
        )
        member = SkeletonMember(class_name='Client', member_name='close', params='', return_type='void')

        assert _is_referenced_from_another_module(tmp_path, 'src.kb.client', owning_path, member)

    def test_a_typescript_export_never_imported_elsewhere_is_not_cross_module(self, tmp_path: Path) -> None:
        owning_path = tmp_path / 'src/kb/client.ts'
        _write(owning_path, "export class Client {\n  helper(): void {}\n}\n")
        member = SkeletonMember(class_name='Client', member_name='helper', params='', return_type='void')

        assert not _is_referenced_from_another_module(tmp_path, 'src.kb.client', owning_path, member)


class TestNewCrossModuleTypeScriptExportBlocks:
    def test_a_new_exported_typescript_function_used_elsewhere_blocks_the_review(self, tmp_path: Path) -> None:
        # B8: check-conformance classifies a new cross-module TypeScript export as
        # added_cross_module, without needing the deferred full signature parser --
        # only cheap exported-name enumeration (find_exported_names) and a regex-based
        # import scan (references_name), same cost tier as Python's ast-based check.
        _write(
            tmp_path / 'src/kb/client.ts',
            "export class Client {\n  query(x: string): string[] {\n    return []\n  }\n}\n\n"
            "export function reconnect(): void {}\n",
        )
        _write(
            tmp_path / 'src/kb/consumer.ts',
            "import { reconnect } from './client'\n\nreconnect()\n",
        )
        index_text = '- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]'

        report = classify_conformance(tmp_path, index_text)

        assert any(b.qualified_name == 'reconnect' and b.kind == 'added_cross_module' for b in report.blockers)

    def test_a_new_exported_typescript_function_never_imported_elsewhere_only_finds(self, tmp_path: Path) -> None:
        _write(
            tmp_path / 'src/kb/client.ts',
            "export class Client {\n  query(x: string): string[] {\n    return []\n  }\n}\n\n"
            "export function helper(): void {}\n",
        )
        index_text = '- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]'

        report = classify_conformance(tmp_path, index_text)

        assert not any(b.qualified_name == 'helper' for b in report.blockers)
        assert any(f.qualified_name == 'helper' and f.kind == 'added_internal' for f in report.findings)


class TestNonPythonEntriesArePassedThroughUnclassified:
    def test_a_typescript_entry_never_crashes_and_produces_no_blockers(self, tmp_path: Path) -> None:
        _write(tmp_path / 'src/kb/client.ts', "export class Client {\n  query(x: string): string[] {\n    return []\n  }\n}\n")
        index_text = '- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]'

        report = classify_conformance(tmp_path, index_text)

        assert report.blockers == ()
        assert report.findings == ()
        assert 'src/kb/client.ts' in report.updated_skeleton_index


class TestTypeScriptEntryRoundTripsThroughWriteBack:
    """B1: parse_signature -> render -> re-parse yields the same structure. A
    TypeScript entry's dotted-looking type must survive the write-back path
    unchanged -- if the first parse were to run it through Python's dotted-import
    extraction, the re-rendered index would silently lose the qualifier."""

    def test_a_dotted_looking_typescript_return_type_survives_write_back_unchanged(self, tmp_path: Path) -> None:
        _write(tmp_path / 'src/kb/client.ts', "export class Client {\n  query(x: string): string[] {\n    return []\n  }\n}\n")
        index_text = '- `src/kb/client.ts` :: Client.query(cypher: string) -> kb.Result'

        report = classify_conformance(tmp_path, index_text)
        reparsed = parse_skeleton_index(report.updated_skeleton_index)

        assert reparsed[0].members[0].return_type == 'kb.Result'
        assert reparsed[0].members[0].required_imports == frozenset()


class TestMalformedPythonFileFailsCleanlyNotWithATraceback:
    def test_a_syntax_error_in_the_owning_file_raises_a_clean_conformance_error(self, tmp_path: Path) -> None:
        _write(tmp_path / 'src/kb/client.py', 'class Neo4jClient(:\n    def broken(\n')
        index_text = '- `src/kb/client.py` :: Neo4jClient.query(cypher: str) -> list[dict]'

        try:
            classify_conformance(tmp_path, index_text)
            raise AssertionError('expected ConformanceParseError')
        except ConformanceParseError as e:
            assert 'client.py' in str(e)


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
