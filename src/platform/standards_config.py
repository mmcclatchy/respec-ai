import json
import tomllib
from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack


DATA_DIR = Path(__file__).parent / 'data'
STANDARDS_DIRNAME = 'standards'
NO_PREFERENCE = 'no_preference'

RULE_SECTIONS: dict[str, str] = {
    'naming': 'Naming',
    'imports': 'Imports',
    'type_system': 'Type System',
    'documentation': 'Documentation',
    'error_handling': 'Error Handling',
    'code_structure': 'Code Structure',
}

STACK_SCHEMA_VERSION = 1
LANGUAGE_SCHEMA_VERSION = 1


def _toml_quote(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _toml_array(values: list[str]) -> str:
    return '[' + ', '.join(_toml_quote(v) for v in values) + ']'


def _render_testing_markdown(testing: dict[str, str | list[str]] | None) -> str:
    if not testing:
        return ''

    framework = str(testing.get('framework', '')).strip()
    location = str(testing.get('location', '')).strip()
    naming = str(testing.get('naming', '')).strip()
    extras = testing.get('extras') or []

    lines = []
    if framework:
        lines.append(f'- Framework: {framework}')
    if location:
        lines.append(f'- Location: {location}')
    if naming:
        lines.append(f'- Naming: {naming}')
    for extra in extras:
        if str(extra).strip():
            lines.append(f'- {str(extra).strip()}')

    if not lines:
        return ''

    return '## Testing\n\n' + '\n'.join(lines)


def _render_rules_markdown(rules: dict[str, list[str]]) -> str:
    sections: list[str] = []
    for key, label in RULE_SECTIONS.items():
        values = [v.strip() for v in rules.get(key, []) if str(v).strip()]
        if values:
            sections.append(f'### {label}\n' + '\n'.join(f'- {v}' for v in values))

    if not sections:
        return ''
    return '## Coding Standards\n\n' + '\n\n'.join(sections)


def _load_language_standards_defaults() -> dict[str, dict]:
    standards_path = DATA_DIR / 'language_standards.json'
    return json.loads(standards_path.read_text(encoding='utf-8'))


def available_languages() -> list[str]:
    defaults = _load_language_standards_defaults()
    languages = sorted(defaults.keys())
    if 'universal' not in languages:
        languages.insert(0, 'universal')
    return languages


def _split_optional_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(',') if part.strip()]


def render_stack_toml(stack: ProjectStack) -> str:
    lines = [
        f'schema_version = {STACK_SCHEMA_VERSION}',
        '',
        '[project]',
        f'language = {_toml_quote(stack.language or "")}',
        f'languages = {_toml_array(_split_optional_csv(stack.language))}',
        '',
        '[stack]',
        f'backend_framework = {_toml_quote(stack.backend_framework or "")}',
        f'frontend_framework = {_toml_quote(stack.frontend_framework or "")}',
        f'package_manager = {_toml_quote(stack.package_manager or "")}',
        f'runtime_version = {_toml_quote(stack.runtime_version or "")}',
        f'database = {_toml_quote(stack.database or "")}',
        f'api_style = {_toml_quote(stack.api_style or "")}',
        f'architecture = {_toml_quote(stack.architecture or "")}',
        f'type_checker = {_toml_quote(stack.type_checker or "")}',
        f'css_framework = {_toml_quote(stack.css_framework or "")}',
        f'ui_components = {_toml_quote(stack.ui_components or "")}',
        f'async_runtime = {str(bool(stack.async_runtime)).lower()}',
        '',
        '[workflow]',
        f'standards_phase = {_toml_quote("phase2")}',
        '',
    ]
    return '\n'.join(lines)


def render_stack_markdown_from_toml(stack_data: dict) -> str:
    project = stack_data.get('project', {})
    stack = stack_data.get('stack', {})
    language = str(project.get('language', '')).strip()
    lines = ['# Project Stack']

    if language:
        runtime = str(stack.get('runtime_version', '')).strip()
        language_line = language if not runtime else f'{language} {runtime}'
        lines.extend(['', '## Languages', f'- {language_line}'])

    backend_lines: list[str] = []
    if str(stack.get('backend_framework', '')).strip():
        backend_lines.append(f'- Framework: {stack["backend_framework"]}')
    if str(stack.get('package_manager', '')).strip():
        backend_lines.append(f'- Package Manager: {stack["package_manager"]}')
    if isinstance(stack.get('async_runtime'), bool):
        backend_lines.append(f'- Async: {"Yes" if stack["async_runtime"] else "No"}')
    if backend_lines:
        lines.extend(['', '## Backend', *backend_lines])

    frontend_lines: list[str] = []
    if str(stack.get('frontend_framework', '')).strip():
        frontend_lines.append(f'- Framework: {stack["frontend_framework"]}')
    if str(stack.get('css_framework', '')).strip():
        frontend_lines.append(f'- CSS: {stack["css_framework"]}')
    if str(stack.get('ui_components', '')).strip():
        frontend_lines.append(f'- Components: {stack["ui_components"]}')
    if frontend_lines:
        lines.extend(['', '## Frontend', *frontend_lines])

    if str(stack.get('database', '')).strip():
        lines.extend(['', '## Database', f'- {stack["database"]}'])

    arch_parts: list[str] = []
    if str(stack.get('architecture', '')).strip():
        arch_parts.append(str(stack['architecture']).strip())
    if str(stack.get('api_style', '')).strip():
        arch_parts.append(f'{str(stack["api_style"]).upper()} API')
    if arch_parts:
        lines.extend(['', '## Architecture', f'- {", ".join(arch_parts)}'])

    lines.append('')
    return '\n'.join(lines)


def _rules_from_defaults(lang_data: dict) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    for key in RULE_SECTIONS:
        values = lang_data.get(key, [])
        rules[key] = [str(v).strip() for v in values if str(v).strip()]
    return rules


def _universal_defaults() -> dict[str, list[str]]:
    return {
        'naming': [NO_PREFERENCE],
        'imports': [
            'No inline imports — all imports at file top',
            'Exception only for circular dependency resolution',
        ],
        'type_system': [NO_PREFERENCE],
        'documentation': [
            'Comments: non-obvious business logic only',
            'Do not add comments that restate obvious code behavior',
        ],
        'error_handling': [
            'Fail fast — validate inputs early and reject invalid state',
            'Use specific exceptions — no catch-all handlers',
            'No silent failures — log or re-raise errors explicitly',
        ],
        'code_structure': [
            'No hardcoded secrets or credentials in source code',
            'No production logic in test files and no test logic in production code',
            'No PII or secrets in logs',
            'Pin dependency versions for reproducible builds',
        ],
    }


def build_language_defaults(lang: str, tooling: LanguageTooling | None = None) -> dict:
    all_defaults = _load_language_standards_defaults()
    lang_data = all_defaults.get(lang, {})
    testing = lang_data.get('testing', {})

    commands = {
        'test': tooling.test_command if tooling else '',
        'coverage': tooling.coverage_command if tooling else '',
        'type_check': tooling.check_command if tooling else '',
        'lint': tooling.lint_command if tooling else '',
    }
    if lang == 'universal':
        commands = {k: NO_PREFERENCE for k in commands}

    return {
        'schema_version': LANGUAGE_SCHEMA_VERSION,
        'language': lang,
        'commands': commands,
        'testing': {
            'framework': str(testing.get('framework', tooling.test_runner if tooling else '')).strip(),
            'location': str(testing.get('location', '')).strip(),
            'naming': str(testing.get('naming', '')).strip(),
            'extras': [str(x).strip() for x in testing.get('extras', []) if str(x).strip()],
        },
        'rules': _universal_defaults() if lang == 'universal' else _rules_from_defaults(lang_data),
    }


def build_language_template(lang: str) -> dict:
    return {
        'schema_version': LANGUAGE_SCHEMA_VERSION,
        'language': lang,
        'commands': {
            'test': '',
            'coverage': '',
            'type_check': '',
            'lint': '',
        },
        'testing': {
            'framework': '',
            'location': '',
            'naming': '',
            'extras': [],
        },
        'rules': {key: [] for key in RULE_SECTIONS},
    }


def render_language_toml(language_data: dict) -> str:
    commands = language_data.get('commands', {})
    testing = language_data.get('testing', {})
    rules = language_data.get('rules', {})
    lines = [
        f'schema_version = {language_data.get("schema_version", LANGUAGE_SCHEMA_VERSION)}',
        f'language = {_toml_quote(str(language_data.get("language", "")).strip())}',
        '',
        '[commands]',
        f'test = {_toml_quote(str(commands.get("test", "")).strip())}',
        f'coverage = {_toml_quote(str(commands.get("coverage", "")).strip())}',
        f'type_check = {_toml_quote(str(commands.get("type_check", "")).strip())}',
        f'lint = {_toml_quote(str(commands.get("lint", "")).strip())}',
        '',
        '[testing]',
        f'framework = {_toml_quote(str(testing.get("framework", "")).strip())}',
        f'location = {_toml_quote(str(testing.get("location", "")).strip())}',
        f'naming = {_toml_quote(str(testing.get("naming", "")).strip())}',
        f'extras = {_toml_array([str(x).strip() for x in testing.get("extras", []) if str(x).strip()])}',
        '',
        '[rules]',
    ]
    for section in RULE_SECTIONS:
        values = [str(v).strip() for v in rules.get(section, []) if str(v).strip()]
        lines.append(f'{section} = {_toml_array(values)}')
    lines.append('')
    return '\n'.join(lines)


def render_language_markdown_from_toml(language_data: dict) -> str:
    language = str(language_data.get('language', '')).strip() or 'Language'
    commands = language_data.get('commands', {})
    rules = language_data.get('rules', {})
    testing = language_data.get('testing', {})

    lines = [f'# {language.title()}', '', '## Commands', '']
    lines.append(f'- **Test**: `{str(commands.get("test", "")).strip() or "none"}`')
    lines.append(f'- **Coverage**: `{str(commands.get("coverage", "")).strip() or "none"}`')
    lines.append(f'- **Type check**: `{str(commands.get("type_check", "")).strip() or "none"}`')
    lines.append(f'- **Lint**: `{str(commands.get("lint", "")).strip() or "none"}`')

    testing_md = _render_testing_markdown(testing)
    if testing_md:
        lines.extend(['', testing_md])

    coding_md = _render_rules_markdown(rules)
    if coding_md:
        lines.extend(['', coding_md])

    lines.append('')
    return '\n'.join(lines)


def load_toml_file(path: Path) -> dict:
    with path.open('rb') as f:
        return tomllib.load(f)


def _is_incomplete_value(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or lowered.startswith('todo') or lowered.startswith('[todo')


def _validate_language_config(language_data: dict, path: Path) -> list[str]:
    errors: list[str] = []
    schema_version = language_data.get('schema_version')
    if schema_version != LANGUAGE_SCHEMA_VERSION:
        errors.append(
            f'{path}: unsupported schema_version={schema_version!r} (expected {LANGUAGE_SCHEMA_VERSION})'
        )

    language = str(language_data.get('language', '')).strip().lower()
    commands = language_data.get('commands') or {}
    for command_key in ('test', 'coverage', 'type_check', 'lint'):
        value = str(commands.get(command_key, '')).strip()
        if language == 'universal' and value.lower() == NO_PREFERENCE:
            continue
        if _is_incomplete_value(value):
            errors.append(f'{path}: commands.{command_key} is required')

    rules = language_data.get('rules') or {}
    for section in RULE_SECTIONS:
        values = [str(v).strip() for v in rules.get(section, []) if str(v).strip()]
        if not values:
            errors.append(f'{path}: rules.{section} must have at least one rule or "{NO_PREFERENCE}"')
            continue
        if all(v.lower() == NO_PREFERENCE for v in values):
            continue
        for value in values:
            if value.lower() == NO_PREFERENCE:
                continue
            if _is_incomplete_value(value):
                errors.append(f'{path}: rules.{section} contains incomplete placeholder value: {value!r}')
    return errors


def validate_project_config(project_path: Path) -> list[str]:
    config_dir = project_path / '.respec-ai' / 'config'
    stack_toml = config_dir / 'stack.toml'
    standards_dir = config_dir / STANDARDS_DIRNAME
    errors: list[str] = []

    if not stack_toml.exists():
        errors.append(f'Missing required file: {stack_toml}')
    else:
        try:
            stack_data = load_toml_file(stack_toml)
            schema_version = stack_data.get('schema_version')
            if schema_version != STACK_SCHEMA_VERSION:
                errors.append(
                    f'{stack_toml}: unsupported schema_version={schema_version!r} (expected {STACK_SCHEMA_VERSION})'
                )
        except Exception as e:
            errors.append(f'{stack_toml}: failed to parse TOML ({e})')

    if not standards_dir.exists():
        errors.append(f'Missing required directory: {standards_dir}')
        return errors

    language_files = sorted(standards_dir.glob('*.toml'))
    if not language_files:
        errors.append(f'No standards TOML files found in {standards_dir}')
        return errors

    for path in language_files:
        try:
            language_data = load_toml_file(path)
        except Exception as e:
            errors.append(f'{path}: failed to parse TOML ({e})')
            continue
        errors.extend(_validate_language_config(language_data, path))

    return errors


def render_markdown_mirrors(project_path: Path) -> list[Path]:
    config_dir = project_path / '.respec-ai' / 'config'
    standards_dir = config_dir / STANDARDS_DIRNAME
    written: list[Path] = []

    stack_toml = config_dir / 'stack.toml'
    if stack_toml.exists():
        stack_data = load_toml_file(stack_toml)
        stack_md = config_dir / 'stack.md'
        stack_md.write_text(render_stack_markdown_from_toml(stack_data), encoding='utf-8')
        written.append(stack_md)

    if not standards_dir.exists():
        return written

    for standards_toml in sorted(standards_dir.glob('*.toml')):
        language_data = load_toml_file(standards_toml)
        language = str(language_data.get('language', standards_toml.stem)).strip() or standards_toml.stem
        language_md = config_dir / f'{language}.md'
        language_md.write_text(render_language_markdown_from_toml(language_data), encoding='utf-8')
        written.append(language_md)

    return written


def write_project_config_files(
    project_path: Path,
    stack: ProjectStack,
    tooling: dict[str, LanguageTooling],
) -> list[Path]:
    config_dir = project_path / '.respec-ai' / 'config'
    standards_dir = config_dir / STANDARDS_DIRNAME
    config_dir.mkdir(parents=True, exist_ok=True)
    standards_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    stack_toml = config_dir / 'stack.toml'
    if not stack_toml.exists():
        stack_toml.write_text(render_stack_toml(stack), encoding='utf-8')
        written.append(stack_toml)

    universal_toml = standards_dir / 'universal.toml'
    if not universal_toml.exists():
        universal_data = build_language_defaults('universal')
        universal_toml.write_text(render_language_toml(universal_data), encoding='utf-8')
        written.append(universal_toml)

    for lang, lang_tooling in tooling.items():
        lang_toml = standards_dir / f'{lang}.toml'
        if not lang_toml.exists():
            lang_data = build_language_defaults(lang, lang_tooling)
            lang_toml.write_text(render_language_toml(lang_data), encoding='utf-8')
            written.append(lang_toml)

    for mirror in render_markdown_mirrors(project_path):
        if mirror not in written:
            written.append(mirror)

    return written
