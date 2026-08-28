import json
import tomllib
from pathlib import Path

from src.platform.models import LanguageStackProfile, LanguageTooling, ProjectStack
from src.platform.standards_config import (
    available_languages,
    build_language_defaults,
    language_testing_convention,
    render_language_toml,
    render_stack_toml,
    resolve_languages_for_paths,
    validate_project_config,
    write_project_config_files,
)
from src.platform.tooling_defaults import apply_stack_to_tooling, detect_project_stack, detect_project_tooling


def test_language_testing_convention_returns_typescripts_own_naming_not_pythons() -> None:
    python_convention = language_testing_convention('python')
    typescript_convention = language_testing_convention('typescript')

    assert python_convention['naming'] == 'test_{function}_{scenario}'
    assert typescript_convention['naming'] == 'describe/it blocks with clear descriptions'
    assert python_convention['location'] != typescript_convention['location']


def test_write_project_config_files_creates_canonical_toml(tmp_path: Path) -> None:
    stack = ProjectStack(
        language='python',
        backend_framework='fastapi',
        language_stack={'python': LanguageStackProfile(package_manager='uv')},
    )
    tooling = {
        'python': LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy .',
            linter='ruff',
            lint_command='ruff check .',
        )
    }

    written = write_project_config_files(tmp_path, stack, tooling)

    config_dir = tmp_path / '.respec-ai' / 'config'
    assert (config_dir / 'stack.toml').exists()
    assert (config_dir / 'standards' / 'universal.toml').exists()
    assert (config_dir / 'standards' / 'python.toml').exists()
    assert len(written) == 3


def test_validate_project_config_passes_for_generated_defaults(tmp_path: Path) -> None:
    stack = ProjectStack(
        language='python',
        backend_framework='fastapi',
        language_stack={'python': LanguageStackProfile(package_manager='uv')},
    )
    tooling = {
        'python': LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy .',
            linter='ruff',
            lint_command='ruff check .',
        )
    }
    write_project_config_files(tmp_path, stack, tooling)
    errors = validate_project_config(tmp_path)
    assert errors == []


def test_write_project_config_files_is_idempotent_when_files_exist(tmp_path: Path) -> None:
    stack = ProjectStack(language='python')
    tooling = {
        'python': LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy .',
            linter='ruff',
            lint_command='ruff check .',
        )
    }
    write_project_config_files(tmp_path, stack, tooling)
    second_write = write_project_config_files(tmp_path, stack, tooling)
    assert second_write == []


def test_language_defaults_have_starter_commands_and_rules() -> None:
    for language in available_languages():
        defaults = build_language_defaults(language)
        commands = defaults.get('commands', {})
        rules = defaults.get('rules', {})

        if language == 'universal':
            assert commands == {}
        else:
            for key in ('test', 'coverage', 'type_check', 'lint'):
                assert str(commands.get(key, '')).strip()

        for section in ('naming', 'imports', 'type_system', 'documentation', 'error_handling', 'code_structure'):
            values = [str(v).strip() for v in rules.get(section, []) if str(v).strip()]
            assert values


def test_universal_render_omits_commands_section() -> None:
    rendered = render_language_toml(build_language_defaults('universal'))
    assert '[commands]' not in rendered
    assert '[testing]' not in rendered


def test_render_language_toml_renders_testing_extras_vertically() -> None:
    rendered = render_language_toml(
        {
            'schema_version': 1,
            'language': 'terraform',
            'commands': {
                'test': 'terraform test',
                'coverage': 'no_preference',
                'type_check': 'no_preference',
                'lint': 'tflint',
            },
            'testing': {
                'framework': 'terraform test (native)',
                'location': 'tests/ directory or module-level test fixtures',
                'naming': 'module_or_resource_scenario_expected_result',
                'extras': [
                    'Use `terraform fmt -check -recursive` and `terraform validate` in CI before apply',
                    'Use `tflint` for Terraform linting in CI',
                    'Use `trivy config` as a security/misconfiguration scan in CI',
                ],
            },
            'rules': {
                'naming': ['Variables/outputs/locals: snake_case'],
                'imports': ['Pin provider and module versions explicitly'],
                'type_system': ['Use explicit variable types for all inputs'],
                'documentation': ['Document module inputs/outputs and required providers'],
                'error_handling': ['Fail fast with variable validation and preconditions for invariants'],
                'code_structure': ['Keep modules focused on one cohesive infrastructure concern'],
            },
        }
    )
    assert 'extras = [' in rendered
    assert '  "Use `terraform fmt -check -recursive` and `terraform validate` in CI before apply",' in rendered
    assert '  "Use `tflint` for Terraform linting in CI",' in rendered
    assert '  "Use `trivy config` as a security/misconfiguration scan in CI",' in rendered


def _python_tooling() -> LanguageTooling:
    return LanguageTooling(
        test_runner='pytest',
        test_command='pytest --tb=short -v',
        coverage_command='pytest --cov',
        checker='mypy',
        check_command='mypy src/',
        linter='ruff',
        lint_command='ruff check .',
    )


def _typescript_tooling() -> LanguageTooling:
    return LanguageTooling(
        test_runner='vitest',
        test_command='npx vitest run',
        coverage_command='npx vitest run --coverage',
        checker='tsc',
        check_command='npx tsc --noEmit',
        linter='eslint',
        lint_command='npx eslint src/',
    )


def _table_lines(rendered: str, table: str) -> list[str]:
    lines = rendered.splitlines()
    start = lines.index(f'[{table}]') + 1
    end = start
    while end < len(lines) and lines[end].strip():
        end += 1
    return lines[start:end]


class TestPolyglotStackRendering:
    def test_frontend_framework_lands_under_typescript_not_python(self) -> None:
        """B1: a Python backend + React (TypeScript) frontend puts frontend_framework under
        [language.typescript], not [language.python] (F2)."""
        stack = ProjectStack(
            language='python',
            languages=['python', 'typescript'],
            backend_framework='fastapi',
            language_stack={
                'python': LanguageStackProfile(package_manager='uv'),
                'typescript': LanguageStackProfile(frontend_framework='react', package_manager='npm'),
            },
        )
        tooling = {'python': _python_tooling(), 'typescript': _typescript_tooling()}

        rendered = render_stack_toml(stack, tooling)

        python_lines = _table_lines(rendered, 'language.python')
        typescript_lines = _table_lines(rendered, 'language.typescript')
        assert 'frontend_framework = ""' in python_lines
        assert 'frontend_framework = "react"' in typescript_lines

    def test_css_framework_and_ui_components_reach_disk_and_survive_rerender(self) -> None:
        """B3/F23: css_framework and ui_components were modeled but never rendered."""
        stack = ProjectStack(
            language='typescript',
            languages=['typescript'],
            language_stack={
                'typescript': LanguageStackProfile(
                    frontend_framework='react', css_framework='tailwindcss', ui_components='shadcn'
                )
            },
        )
        tooling = {'typescript': _typescript_tooling()}

        rendered = render_stack_toml(stack, tooling)
        parsed = tomllib.loads(rendered)

        assert parsed['language']['typescript']['css_framework'] == 'tailwindcss'
        assert parsed['language']['typescript']['ui_components'] == 'shadcn'

        rerendered = render_stack_toml(stack, tooling)
        assert rerendered == rendered

    def test_optional_dev_server_keys_round_trip_and_are_optional(self) -> None:
        """B4: dev_command/base_url/storage_state_path round-trip and their absence validates
        clean -- they must never be added to the required *_command tuple."""
        stack = ProjectStack(
            language='typescript',
            languages=['typescript'],
            language_stack={
                'typescript': LanguageStackProfile(
                    frontend_framework='react',
                    dev_command='npm run dev',
                    base_url='http://localhost:5173',
                    storage_state_path='.respec-ai/state/storage-state.json',
                )
            },
        )
        tooling = {'typescript': _typescript_tooling()}

        rendered = render_stack_toml(stack, tooling)
        parsed = tomllib.loads(rendered)
        language_table = parsed['language']['typescript']
        assert language_table['dev_command'] == 'npm run dev'
        assert language_table['base_url'] == 'http://localhost:5173'
        assert language_table['storage_state_path'] == '.respec-ai/state/storage-state.json'

    def test_missing_dev_server_keys_validate_clean(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python', language_stack={'python': LanguageStackProfile(package_manager='uv')})
        tooling = {'python': _python_tooling()}
        write_project_config_files(tmp_path, stack, tooling)

        errors = validate_project_config(tmp_path)

        assert errors == []

    def test_polyglot_project_config_validates_clean(self, tmp_path: Path) -> None:
        stack = ProjectStack(
            language='python',
            languages=['python', 'typescript'],
            backend_framework='fastapi',
            language_stack={
                'python': LanguageStackProfile(package_manager='uv'),
                'typescript': LanguageStackProfile(frontend_framework='react', package_manager='npm'),
            },
        )
        tooling = {'python': _python_tooling(), 'typescript': _typescript_tooling()}
        write_project_config_files(tmp_path, stack, tooling)

        errors = validate_project_config(tmp_path)

        assert errors == []

    def test_single_language_stack_toml_matches_pre_polyglot_field_values(self) -> None:
        """B6: the regression guard. A single-language project's existing fields keep the same
        values and key names -- css_framework/ui_components/dev_command/base_url/storage_state_path
        are additive new optional fields, not replacements for what rendered before."""
        stack = ProjectStack(
            language='python',
            languages=['python'],
            backend_framework='fastapi',
            database='postgresql',
            api_style='rest',
            architecture='monolith',
            async_runtime=True,
            language_stack={'python': LanguageStackProfile(package_manager='uv', runtime_version='3.13')},
        )
        tooling = {'python': _python_tooling()}

        rendered = render_stack_toml(stack, tooling)
        parsed = tomllib.loads(rendered)
        python_table = parsed['language']['python']

        assert python_table['runtime_version'] == '3.13'
        assert python_table['package_manager'] == 'uv'
        assert python_table['backend_framework'] == 'fastapi'
        assert python_table['frontend_framework'] == ''
        assert python_table['database'] == 'postgresql'
        assert python_table['api_style'] == 'rest'
        assert python_table['architecture'] == 'monolith'
        assert python_table['async_runtime'] is True
        assert python_table['type_checker'] == 'mypy'
        assert python_table['test_runner'] == 'pytest'
        assert python_table['css_framework'] == ''
        assert python_table['ui_components'] == ''
        assert python_table['dev_command'] == ''
        assert python_table['base_url'] == ''
        assert python_table['storage_state_path'] == ''

    def test_typescript_type_checker_override_is_honored_in_render(self) -> None:
        """B5: a TypeScript project's configured type_checker is honored, not silently dropped."""
        stack = ProjectStack(
            language='typescript',
            languages=['typescript'],
            language_stack={'typescript': LanguageStackProfile(type_checker='tsc')},
        )
        tooling = {'typescript': _typescript_tooling()}

        rendered = render_stack_toml(stack, tooling)
        parsed = tomllib.loads(rendered)

        assert parsed['language']['typescript']['type_checker'] == 'tsc'

    def test_materialization_language_resolution_agrees_with_stack_toml_languages(self, tmp_path: Path) -> None:
        """B7: reconciling with phase 1 -- for a real Python+TypeScript project (tsconfig.json
        present, which is what promotes the detected language to 'typescript' -- see
        `detect_project_tooling`), the extension map (what materialization actually uses for
        per-file dispatch) agrees with the languages `detect_project_stack` puts in stack.toml.
        The extension map stays authoritative; this only asserts the two do not silently disagree."""
        (tmp_path / 'pyproject.toml').write_text('[project]\ndependencies = ["fastapi>=0.100"]\n\n[tool.uv]\n')
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'web', 'dependencies': {'react': '^18.0'}}))
        (tmp_path / 'tsconfig.json').write_text('{}')

        stack = detect_project_stack(tmp_path)
        tooling = apply_stack_to_tooling(detect_project_tooling(tmp_path), stack)
        write_project_config_files(tmp_path, stack, tooling)

        parsed = tomllib.loads((tmp_path / '.respec-ai' / 'config' / 'stack.toml').read_text())
        declared_languages = set(parsed['project']['languages'])

        project_paths = ['src/backend/app.py', 'src/frontend/App.tsx', 'src/frontend/index.ts']
        assert resolve_languages_for_paths(project_paths) == declared_languages == {'python', 'typescript'}

    def test_detected_language_name_can_disagree_with_source_extensions_without_tsconfig(
        self, tmp_path: Path
    ) -> None:
        """Documents a real gap rather than papering over it (B7's spirit, per decisions.md: 'if
        they ever disagree, that is a signal worth surfacing, not a reason to prefer one
        silently'). Detection names the JS/TS half from `tsconfig.json` presence, a build-file
        check; it never scans source files. A project that already has `.tsx` files but has not
        added `tsconfig.json` yet detects as 'javascript' while the extension map resolves those
        files to 'typescript' -- a genuine disagreement. Fixing detection to scan source
        extensions is out of phase 3's scope (see deferred-issues.md); this test exists so the gap
        is asserted, not silently reintroduced."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'web', 'dependencies': {'react': '^18.0'}}))

        stack = detect_project_stack(tmp_path)

        assert stack.languages == ['javascript']
        assert resolve_languages_for_paths(['src/App.tsx']) == {'typescript'}

    def test_end_to_end_python_react_scratch_project(self, tmp_path: Path) -> None:
        """Exit criteria: a real Python+React scratch project detects both languages, puts each
        attribute under the right table, validates clean, and stays clean once dev_command is
        removed (it is optional, never required)."""
        (tmp_path / 'pyproject.toml').write_text('[project]\ndependencies = ["fastapi>=0.100"]\n\n[tool.uv]\n')
        (tmp_path / 'package.json').write_text(
            json.dumps({'name': 'web', 'dependencies': {'react': '^18.0'}})
        )

        stack = detect_project_stack(tmp_path)
        tooling = detect_project_tooling(tmp_path)
        tooling = apply_stack_to_tooling(tooling, stack)

        assert stack.languages == ['python', 'javascript']

        write_project_config_files(tmp_path, stack, tooling)
        assert validate_project_config(tmp_path) == []

        stack_toml = tmp_path / '.respec-ai' / 'config' / 'stack.toml'
        parsed = tomllib.loads(stack_toml.read_text())
        assert parsed['language']['python']['frontend_framework'] == ''
        assert parsed['language']['javascript']['frontend_framework'] == 'react'

        content_without_dev_command = '\n'.join(
            line for line in stack_toml.read_text().splitlines() if not line.startswith('dev_command')
        )
        stack_toml.write_text(content_without_dev_command)
        assert validate_project_config(tmp_path) == []
