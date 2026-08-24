import subprocess
import sys
from pathlib import Path

import pytest

from src.utils.skeleton_generator import (
    SkeletonPathEscapesProjectError,
    extract_existing_signatures,
    generate_skeletons,
    generate_tests,
    merge_new_members,
    parse_skeleton_index,
    parse_test_list,
)

SKELETON_INDEX_TEXT = (
    '- `src/kb/neo4j_client.py` :: Neo4jClient.__init__(uri: str, auth: tuple[str, str]) -> None\n'
    '- `src/kb/neo4j_client.py` :: Neo4jClient.query(cypher: str) -> list[BestPractice]\n'
    '- `src/kb/helpers.py` :: normalize_query(raw: str) -> str, internal, consequential\n'
)

TEST_LIST_TEXT = (
    '- `tests/unit/kb/test_neo4j_client.py::test_reconnects_after_timeout`\n'
    '- `tests/unit/kb/test_neo4j_client.py::test_query_returns_structured_results`\n'
)


def test_skeleton_index_groups_members_under_the_same_path() -> None:
    entries = parse_skeleton_index(SKELETON_INDEX_TEXT)

    by_path = {entry.path: entry for entry in entries}
    assert set(by_path) == {'src/kb/neo4j_client.py', 'src/kb/helpers.py'}
    assert [m.member_name for m in by_path['src/kb/neo4j_client.py'].members] == ['__init__', 'query']


def test_skeleton_index_trailing_tags_do_not_corrupt_the_return_type() -> None:
    entries = parse_skeleton_index(SKELETON_INDEX_TEXT)

    helper_member = next(e for e in entries if e.path == 'src/kb/helpers.py').members[0]
    assert helper_member.return_type == 'str'
    assert helper_member.tags == frozenset({'internal', 'consequential'})


def test_skeleton_index_return_type_containing_a_comma_is_not_split() -> None:
    entries = parse_skeleton_index(
        '- `src/kb/client.py` :: Client.auth(uri: str) -> tuple[str, str]\n'
    )

    member = entries[0].members[0]
    assert member.return_type == 'tuple[str, str]'


def test_test_list_groups_test_names_under_the_same_path() -> None:
    entries = parse_test_list(TEST_LIST_TEXT)

    assert len(entries) == 1
    assert entries[0].path == 'tests/unit/kb/test_neo4j_client.py'
    assert set(entries[0].test_names) == {
        'test_reconnects_after_timeout',
        'test_query_returns_structured_results',
    }


def test_non_bullet_lines_in_skeleton_index_are_ignored() -> None:
    text = SKELETON_INDEX_TEXT + '  (one line per public message — the durable contract)\n'
    entries = parse_skeleton_index(text)
    assert len(entries) == 2


class TestExistingSourceFileIsNeverOverwritten:
    def test_existing_source_file_is_never_overwritten(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        original = 'class Client:\n    def query(self, cypher: str) -> list[str]:\n        return []\n'
        target.write_text(original)

        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        result = generate_skeletons(tmp_path, entries)

        assert target.read_text() == original
        assert target not in result.written_paths
        assert len(result.reconciliation_needed) == 1
        assert result.reconciliation_needed[0].path == 'src/kb/client.py'

    def test_existing_test_file_is_never_overwritten(self, tmp_path: Path) -> None:
        target = tmp_path / 'tests' / 'unit' / 'test_client.py'
        target.parent.mkdir(parents=True)
        original = 'def test_something() -> None:\n    assert True\n'
        target.write_text(original)

        entries = parse_test_list('- `tests/unit/test_client.py::test_something_else`\n')
        result = generate_tests(tmp_path, entries)

        assert target.read_text() == original
        assert target not in result.written_paths
        assert target in result.skipped_existing


def test_a_declined_internal_class_never_gets_a_skeleton_file(tmp_path: Path) -> None:
    # Backstop for README.md cross-cutting risk #1: Step 7 (Skeleton Opt-In) is supposed
    # to strip an unselected "internal, consequential" entry from the Skeleton Index
    # before it ever reaches materialization -- this pins that the generator itself
    # never materializes one, even if that prose step under-performs.
    entries = parse_skeleton_index(
        '- `src/kb/cache.py` :: _Cache.get(key: str) -> str, internal, consequential\n'
    )

    result = generate_skeletons(tmp_path, entries)

    assert result.written_paths == ()
    assert result.reconciliation_needed == ()
    assert not (tmp_path / 'src' / 'kb' / 'cache.py').exists()


def test_a_user_selected_internal_class_still_gets_a_skeleton_file(tmp_path: Path) -> None:
    entries = parse_skeleton_index(
        '- `src/kb/cache.py` :: _Cache.get(key: str) -> str, internal, user-selected\n'
    )

    result = generate_skeletons(tmp_path, entries)

    target = tmp_path / 'src' / 'kb' / 'cache.py'
    assert target in result.written_paths
    assert 'class _Cache:' in target.read_text()


def test_new_skeleton_file_is_written_at_the_named_path(tmp_path: Path) -> None:
    entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')

    result = generate_skeletons(tmp_path, entries)

    target = tmp_path / 'src' / 'kb' / 'client.py'
    assert target in result.written_paths
    assert 'class Client:' in target.read_text()
    assert 'raise NotImplementedError' in target.read_text()


class TestQualifiedTypeReferencesBecomeRealImports:
    def test_a_dotted_return_type_produces_a_matching_import_line(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[kb.models.BestPractice]\n'
        )

        result = generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'from kb.models import BestPractice' in content
        assert 'list[BestPractice]' in content
        assert 'kb.models.BestPractice' not in content
        assert result.written_paths

    def test_a_dotted_param_type_also_produces_an_import(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.store(entry: kb.models.BestPractice) -> None\n'
        )

        result = generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'from kb.models import BestPractice' in content
        assert 'entry: BestPractice' in content
        assert result.written_paths

    def test_multiple_members_referencing_the_same_type_produce_one_deduplicated_import(
        self, tmp_path: Path
    ) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[kb.models.BestPractice]\n'
            '- `src/kb/client.py` :: Client.store(entry: kb.models.BestPractice) -> None\n'
        )

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert content.count('from kb.models import BestPractice') == 1

    def test_builtin_generics_never_produce_a_spurious_import(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> tuple[str, str]\n'
        )

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'import' not in content

    def test_the_plan_document_worked_example_type_checks(self, tmp_path: Path) -> None:
        # docs/phase-refactor/phase-4-skeletons.md's own worked example: Neo4jClient with
        # an async method returning a project-defined type. This is the exact case that
        # previously failed `ty check` with an unresolved-reference error.
        (tmp_path / 'pyproject.toml').write_text(
            '[project]\nname = "scratch"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
        )
        (tmp_path / 'kb').mkdir()
        (tmp_path / 'kb' / '__init__.py').write_text('')
        (tmp_path / 'kb' / 'models.py').write_text('class BestPractice:\n    pass\n')

        entries = parse_skeleton_index(
            '- `src/kb/neo4j_client.py` :: Neo4jClient.__init__(uri: str, auth: tuple[str, str]) -> None\n'
            '- `src/kb/neo4j_client.py` :: Neo4jClient.query(cypher: str) -> list[kb.models.BestPractice], async\n'
        )
        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'neo4j_client.py').read_text()
        assert 'async def query' in content

        ty_executable = str(Path(sys.executable).with_name('ty'))
        result = subprocess.run(
            [ty_executable, 'check', 'src/kb/neo4j_client.py'], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestAsyncTag:
    def test_async_tagged_member_renders_as_async_def(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str], async\n'
        )

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'async def query' in content

    def test_untagged_member_renders_as_plain_def(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        assert 'def query' in content
        assert 'async def query' not in content

    def test_async_combines_with_other_tags_without_corrupting_the_return_type(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: _Cache.query(cypher: str) -> list[str], internal, consequential, async\n'
        )

        member = entries[0].members[0]
        assert member.return_type == 'list[str]'
        assert member.tags == frozenset({'internal', 'consequential', 'async'})


def test_skeleton_reconciliation_reports_both_existing_and_designed_signatures(tmp_path: Path) -> None:
    target = tmp_path / 'src' / 'kb' / 'client.py'
    target.parent.mkdir(parents=True)
    target.write_text('class Client:\n    def query(self) -> list[str]:\n        return []\n')

    entries = parse_skeleton_index(
        '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        '- `src/kb/client.py` :: Client.close() -> None\n'
    )
    result = generate_skeletons(tmp_path, entries)

    choice = result.reconciliation_needed[0]
    assert choice.existing_signatures == ('Client.query() -> list[str]',)
    assert set(choice.designed_signatures) == {
        'Client.query(cypher: str) -> list[str]',
        'Client.close() -> None',
    }


def test_skeleton_reconciliation_shows_a_divergent_signature_not_just_a_matching_name(
    tmp_path: Path,
) -> None:
    # B2: a same-name, different-signature member must be visibly different in the
    # reconciliation diff -- not silently reported as an identical match.
    target = tmp_path / 'src' / 'kb' / 'client.py'
    target.parent.mkdir(parents=True)
    target.write_text('class Client:\n    def query(self) -> list[str]:\n        return []\n')

    entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
    result = generate_skeletons(tmp_path, entries)

    choice = result.reconciliation_needed[0]
    assert choice.existing_signatures != choice.designed_signatures
    assert choice.existing_signatures == ('Client.query() -> list[str]',)
    assert choice.designed_signatures == ('Client.query(cypher: str) -> list[str]',)


class TestMergeAddsOnlyGenuinelyNewMembers:
    def test_merge_appends_a_new_method_without_touching_the_existing_one(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        target.write_text(
            'class Client:\n    def query(self, cypher: str) -> list[str]:\n        return ["real"]\n'
        )

        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
            '- `src/kb/client.py` :: Client.close() -> None\n'
        )
        result = merge_new_members(tmp_path, entries, frozenset({'src/kb/client.py'}))

        assert target in result.merged_paths
        assert result.unresolved_signature_conflicts == ()
        content = target.read_text()
        assert 'return ["real"]' in content
        assert 'def close(self) -> None:' in content
        assert 'raise NotImplementedError' in content

    def test_merge_is_a_no_op_when_every_designed_member_already_exists(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        original = 'class Client:\n    def query(self, cypher: str) -> list[str]:\n        return []\n'
        target.write_text(original)

        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        result = merge_new_members(tmp_path, entries, frozenset({'src/kb/client.py'}))

        assert result.merged_paths == ()
        assert result.unresolved_signature_conflicts == ()
        assert target.read_text() == original

    def test_merge_leaves_paths_not_selected_for_merge_untouched(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        original = 'class Client:\n    def query(self, cypher: str) -> list[str]:\n        return []\n'
        target.write_text(original)

        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.close() -> None\n'
        )
        result = merge_new_members(tmp_path, entries, frozenset())

        assert result.merged_paths == ()
        assert target.read_text() == original

    def test_merge_reports_a_same_name_divergent_signature_as_unresolved_not_as_already_present(
        self, tmp_path: Path
    ) -> None:
        # B2: a same-name member whose signature differs from what's designed must never
        # be silently treated as satisfied -- neither appended (duplicate `def`) nor
        # dropped as a no-op merge, the way plain name matching would.
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        original = 'class Client:\n    def query(self) -> list[str]:\n        return []\n'
        target.write_text(original)

        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        result = merge_new_members(tmp_path, entries, frozenset({'src/kb/client.py'}))

        assert result.merged_paths == ()
        assert result.unresolved_signature_conflicts == ('Client.query(cypher: str) -> list[str]',)
        assert target.read_text() == original

    def test_merged_file_still_type_checks(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        target.write_text('class Client:\n    def query(self, cypher: str) -> list[str]:\n        return []\n')
        (tmp_path / 'pyproject.toml').write_text(
            '[project]\nname = "scratch"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
        )

        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
            '- `src/kb/client.py` :: Client.close() -> None\n'
        )
        merge_new_members(tmp_path, entries, frozenset({'src/kb/client.py'}))

        assert extract_existing_signatures(target) == (
            'Client.query(cypher: str) -> list[str]',
            'Client.close() -> None',
        )
        ty_executable = str(Path(sys.executable).with_name('ty'))
        result = subprocess.run(
            [ty_executable, 'check', 'src/kb/client.py'], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_skeleton_path_cannot_escape_the_project_root(tmp_path: Path) -> None:
    entries = parse_skeleton_index('- `../../etc/evil.py` :: Evil.run() -> None\n')

    with pytest.raises(SkeletonPathEscapesProjectError):
        generate_skeletons(tmp_path, entries)


def _write_pyproject_for_type_checking(tmp_path: Path) -> None:
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\nname = "scratch"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
    )


class TestGeneratedSkeletonsAreExecutable:
    def test_generated_skeletons_type_check(self, tmp_path: Path) -> None:
        _write_pyproject_for_type_checking(tmp_path)
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.__init__(uri: str) -> None\n'
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        generate_skeletons(tmp_path, entries)

        ty_executable = str(Path(sys.executable).with_name('ty'))
        result = subprocess.run(
            [ty_executable, 'check', 'src/kb/client.py'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_generated_skeletons_satisfy_ruff(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        generate_skeletons(tmp_path, entries)

        result = subprocess.run(
            [sys.executable, '-m', 'ruff', 'check', 'src/kb/client.py'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_generated_tests_fail_before_implementation(self, tmp_path: Path) -> None:
        skeleton_entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        test_entries = parse_test_list('- `tests/test_client.py::test_query_returns_a_list`\n')
        generate_skeletons(tmp_path, skeleton_entries)
        generate_tests(tmp_path, test_entries)

        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/test_client.py'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_generated_tests_pass_once_the_seam_is_implemented(self, tmp_path: Path) -> None:
        client_path = tmp_path / 'src' / 'kb' / 'client.py'
        skeleton_entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
        )
        generate_skeletons(tmp_path, skeleton_entries)

        test_path = tmp_path / 'tests' / 'test_client.py'
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(
            'import sys\n'
            f'sys.path.insert(0, {str(tmp_path / "src")!r})\n'
            'from kb.client import Client\n\n\n'
            'def test_query_returns_a_list() -> None:\n'
            "    assert Client().query('x') == []\n"
        )
        client_path.write_text('class Client:\n    def query(self, cypher: str) -> list[str]:\n        return []\n')

        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/test_client.py'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
