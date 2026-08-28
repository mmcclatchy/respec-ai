import shutil
import subprocess
from pathlib import Path

import pytest

from src.utils.materializers import UnsupportedLanguageError, get_materializer
from src.utils.skeleton_generator import (
    generate_skeletons,
    generate_tests,
    merge_new_members,
    parse_skeleton_index,
    parse_test_list,
)

pytestmark_npx = pytest.mark.skipif(shutil.which('npx') is None, reason='npx not available for TS type checking')


def _tsc_check(*paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['npx', '--yes', '-p', 'typescript', 'tsc', '--noEmit', '--target', 'es2020', '--module', 'esnext']
        + [str(p) for p in paths],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_get_materializer_raises_a_clean_error_for_an_unregistered_language() -> None:
    with pytest.raises(UnsupportedLanguageError):
        get_materializer('go', 'src/main.go')


def test_get_materializer_raises_a_clean_error_for_an_unrecognized_extension() -> None:
    with pytest.raises(UnsupportedLanguageError):
        get_materializer(None, 'README.md')


class TestUnsupportedLanguageMaterialization:
    def test_an_unsupported_language_path_is_reported_not_written_and_never_raises(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/main.go` :: Repo.Get(id: string) -> User\n')

        result = generate_skeletons(tmp_path, entries)

        assert result.written_paths == ()
        assert len(result.unmaterialized_paths) == 1
        unmaterialized = result.unmaterialized_paths[0]
        assert unmaterialized.path == 'src/main.go'
        assert 'go' in unmaterialized.reason.lower()
        assert not (tmp_path / 'src' / 'main.go').exists()

    def test_an_unsupported_language_never_gets_python_written_into_it(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/App.vue` :: setup(props: Props) -> void\n')

        result = generate_skeletons(tmp_path, entries)

        assert not (tmp_path / 'src' / 'App.vue').exists()
        assert result.unmaterialized_paths[0].path == 'src/App.vue'

    def test_unsupported_test_list_language_is_reported_not_written(self, tmp_path: Path) -> None:
        entries = parse_test_list('- `tests/App.spec.go::TestSomething`\n')

        result = generate_tests(tmp_path, entries)

        assert result.written_paths == ()
        assert result.unmaterialized_paths[0].path == 'tests/App.spec.go'


class TestPythonMaterializationIsUnchanged:
    def test_python_entry_still_materializes_valid_python(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')

        result = generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        compile(content, 'client.py', 'exec')
        assert result.written_paths


class TestTypeScriptMaterialization:
    def test_typescript_class_entry_materializes_a_real_class(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/Client.ts` :: Client.query(cypher: string) -> string[]\n'
        )

        result = generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'Client.ts').read_text()
        assert 'class Client' in content
        assert "throw new Error('Not implemented')" in content
        assert 'raise NotImplementedError' not in content
        assert result.written_paths

    @pytestmark_npx
    def test_typescript_output_parses_with_real_ts_tooling(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]\n'
            '- `src/kb/client.ts` :: Client.close() -> void\n'
        )
        generate_skeletons(tmp_path, entries)

        result = _tsc_check(tmp_path / 'src' / 'kb' / 'client.ts')
        assert result.returncode == 0, result.stdout + result.stderr

    def test_typescript_function_entry_has_no_self_injected(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index('- `src/kb/util.ts` :: normalize(raw: string) -> string\n')

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'util.ts').read_text()
        assert 'self' not in content

    def test_typescript_async_tag_renders_as_async_function(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.ts` :: Client.query(cypher: string) -> Promise<string[]>, async\n'
        )

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'client.ts').read_text()
        assert 'async' in content

    def test_generated_typescript_tests_use_real_test_syntax(self, tmp_path: Path) -> None:
        entries = parse_test_list('- `tests/client.spec.ts::test_query_returns_results`\n')

        result = generate_tests(tmp_path, entries)

        content = (tmp_path / 'tests' / 'client.spec.ts').read_text()
        assert 'test(' in content
        assert 'raise AssertionError' not in content
        assert result.written_paths


class TestPreExistingTypeScriptFileDoesNotCrash:
    def test_a_pre_existing_ts_file_yields_a_create_only_notice_not_a_syntax_error(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.ts'
        target.parent.mkdir(parents=True)
        target.write_text('export class Client {}\n')

        entries = parse_skeleton_index('- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]\n')
        result = generate_skeletons(tmp_path, entries)

        assert result.reconciliation_needed == ()
        assert result.unintrospectable_paths == ('src/kb/client.ts',)
        # Never overwritten and never has Python written into it.
        assert target.read_text() == 'export class Client {}\n'


class TestMergeNeverAttemptsToIntrospectAForeignLanguage:
    def test_merge_on_a_typescript_path_degrades_cleanly_never_a_syntax_error(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.ts'
        target.parent.mkdir(parents=True)
        target.write_text('export class Client {}\n')

        entries = parse_skeleton_index('- `src/kb/client.ts` :: Client.query(cypher: string) -> string[]\n')
        result = merge_new_members(tmp_path, entries, frozenset({'src/kb/client.ts'}))

        assert result.merged_paths == ()
        assert result.unintrospectable_paths == ('src/kb/client.ts',)
        assert target.read_text() == 'export class Client {}\n'

    def test_merge_on_a_syntactically_broken_python_file_never_raises_a_traceback(self, tmp_path: Path) -> None:
        # F6: a Python traceback as a phase-failure diagnostic is a Python-invisibility
        # violation, not just a robustness bug -- the file exists, is on the Python
        # extension, but ast.parse cannot read it.
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        target.write_text('class Client(:\n    def broken(\n')

        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        result = merge_new_members(tmp_path, entries, frozenset({'src/kb/client.py'}))

        assert result.merged_paths == ()
        assert result.unintrospectable_paths == ('src/kb/client.py',)
        assert target.read_text() == 'class Client(:\n    def broken(\n'


class TestMixedLanguageSingleRun:
    def test_a_python_and_a_typescript_entry_in_one_run_each_materialize_correctly(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n'
            '- `src/web/Client.ts` :: Client.query(cypher: string) -> string[]\n'
        )

        result = generate_skeletons(tmp_path, entries)

        py_content = (tmp_path / 'src' / 'kb' / 'client.py').read_text()
        ts_content = (tmp_path / 'src' / 'web' / 'Client.ts').read_text()
        assert 'raise NotImplementedError' in py_content
        assert "throw new Error('Not implemented')" in ts_content
        assert 'raise NotImplementedError' not in ts_content
        assert "throw new Error('Not implemented')" not in py_content
        assert len(result.written_paths) == 2


class TestPreExistingPythonFileStillReconciles:
    def test_a_pre_existing_py_file_still_yields_signature_reconciliation(self, tmp_path: Path) -> None:
        target = tmp_path / 'src' / 'kb' / 'client.py'
        target.parent.mkdir(parents=True)
        target.write_text('class Client:\n    def query(self) -> list[str]:\n        return []\n')

        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> list[str]\n')
        result = generate_skeletons(tmp_path, entries)

        assert result.unintrospectable_paths == ()
        assert len(result.reconciliation_needed) == 1
        assert result.reconciliation_needed[0].existing_signatures == ('Client.query() -> list[str]',)


class TestPythonOnlyPhaseIsUnaffectedByLanguageDispatch:
    """B6, the regression guard, pinned by name: a phase with no TypeScript files must
    materialize identically before and after wiring signature-parse dispatch through
    the language seam -- the dispatch change must be invisible to an all-Python phase."""

    def test_a_python_only_index_with_a_dotted_import_materializes_exactly_as_before(
        self, tmp_path: Path
    ) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/neo4j_client.py` :: Neo4jClient.__init__(uri: str, auth: tuple[str, str]) -> None\n'
            '- `src/kb/neo4j_client.py` :: Neo4jClient.query(cypher: str) -> list[kb.models.BestPractice]\n'
        )

        result = generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'kb' / 'neo4j_client.py').read_text()
        assert content == (
            'from kb.models import BestPractice\n\n\n'
            'class Neo4jClient:\n'
            '    def __init__(self, uri: str, auth: tuple[str, str]) -> None:\n'
            '        raise NotImplementedError\n\n'
            '    def query(self, cypher: str) -> list[BestPractice]:\n'
            '        raise NotImplementedError\n'
        )
        assert result.written_paths


class TestSignatureParsingDispatchesByLanguage:
    """B2: parse_skeleton_index must route each entry through its own language's
    parse_signature, not always through Python's -- a polyglot phase is the real case
    the seam exists for."""

    def test_a_typescript_entrys_dotted_looking_type_is_not_treated_as_a_python_import(self) -> None:
        entries = parse_skeleton_index('- `src/kb/Client.ts` :: Client.query(cypher: string) -> kb.Result\n')

        member = entries[0].members[0]

        assert member.return_type == 'kb.Result'
        assert member.required_imports == frozenset()

    def test_a_python_entrys_dotted_type_still_extracts_a_real_import(self) -> None:
        entries = parse_skeleton_index('- `src/kb/client.py` :: Client.query(cypher: str) -> kb.models.Result\n')

        member = entries[0].members[0]

        assert member.return_type == 'Result'
        assert member.required_imports == frozenset({('kb.models', 'Result')})

    def test_a_python_and_a_typescript_entry_parse_correctly_in_the_same_call(self) -> None:
        entries = parse_skeleton_index(
            '- `src/kb/client.py` :: Client.query(cypher: str) -> kb.models.Result\n'
            '- `src/kb/Client.ts` :: Client.query(cypher: string) -> kb.Result\n'
        )
        by_path = {e.path: e.members[0] for e in entries}

        assert by_path['src/kb/client.py'].return_type == 'Result'
        assert by_path['src/kb/client.py'].required_imports == frozenset({('kb.models', 'Result')})
        assert by_path['src/kb/Client.ts'].return_type == 'kb.Result'
        assert by_path['src/kb/Client.ts'].required_imports == frozenset()

    def test_an_unsupported_language_path_still_parses_structurally_without_raising(self) -> None:
        entries = parse_skeleton_index('- `src/main.go` :: Repo.Get(id: string) -> User\n')

        member = entries[0].members[0]

        assert member.member_name == 'Get'
        assert member.class_name == 'Repo'
        assert member.return_type == 'User'


class TestComponentContractCarriesTypedProps:
    """B4: a component entry carries prop names and types, not just a component name --
    expressed inside the existing name(params) -> Return grammar (decisions.md: no new
    syntax for Vue/Svelte-incompatible component forms)."""

    def test_a_react_component_entry_preserves_its_inline_props_type_verbatim(self) -> None:
        entries = parse_skeleton_index(
            '- `src/components/LoginForm.tsx` :: LoginForm(props: '
            '{ email: string; password: string; onSubmit: (data: LoginData) => void }) '
            '-> JSX.Element\n'
        )

        member = entries[0].members[0]

        assert member.member_name == 'LoginForm'
        assert member.class_name is None
        assert member.params == (
            'props: { email: string; password: string; onSubmit: (data: LoginData) => void }'
        )
        assert member.return_type == 'JSX.Element'

    def test_a_rendered_component_skeleton_is_a_real_exported_function(self, tmp_path: Path) -> None:
        entries = parse_skeleton_index(
            '- `src/components/LoginForm.tsx` :: LoginForm(props: LoginFormProps) -> JSX.Element\n'
        )

        generate_skeletons(tmp_path, entries)

        content = (tmp_path / 'src' / 'components' / 'LoginForm.tsx').read_text()
        assert 'export function LoginForm(props: LoginFormProps): JSX.Element' in content
        materializer = get_materializer('typescript', 'src/components/LoginForm.tsx')
        assert materializer.find_exported_names(content) == frozenset({'LoginForm'})


class TestTestListNamingFollowsTheLanguagesOwnConvention:
    """B3: TypeScript test entries are not pytest node IDs wearing a .spec.ts
    extension -- the free-text description form language_standards.json describes
    for TypeScript ("describe/it blocks with clear descriptions") must survive
    parse -> render unmangled."""

    def test_a_typescript_test_entry_with_a_prose_description_renders_idiomatically(self, tmp_path: Path) -> None:
        entries = parse_test_list('- `tests/Client.spec.ts::renders the error state when submit fails`\n')

        result = generate_tests(tmp_path, entries)

        content = (tmp_path / 'tests' / 'Client.spec.ts').read_text()
        assert "test('renders the error state when submit fails'" in content
        assert 'test_' not in content
        assert result.written_paths
