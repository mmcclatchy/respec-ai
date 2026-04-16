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

STACK_SCHEMA_VERSION = 2
LANGUAGE_SCHEMA_VERSION = 1


def _toml_quote(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _toml_array(values: list[str]) -> str:
    return '[' + ', '.join(_toml_quote(v) for v in values) + ']'


def _load_language_standards_defaults() -> dict[str, dict]:
    standards_path = DATA_DIR / 'language_standards.json'
    return json.loads(standards_path.read_text(encoding='utf-8'))


def available_languages() -> list[str]:
    defaults = _load_language_standards_defaults()
    languages = sorted(defaults.keys())
    if 'universal' not in languages:
        languages.insert(0, 'universal')
    return languages


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


def _validate_stack_v2(stack_data: dict, path: Path) -> list[str]:
    errors: list[str] = []
    schema_version = stack_data.get('schema_version')
    if schema_version != STACK_SCHEMA_VERSION:
        errors.append(f'{path}: unsupported schema_version={schema_version!r} (expected {STACK_SCHEMA_VERSION})')
        return errors

    project = stack_data.get('project') or {}
    primary_language = str(project.get('primary_language', '')).strip()
    languages = [str(v).strip() for v in project.get('languages', []) if str(v).strip()]
    execution = stack_data.get('execution') or {}

    if not languages:
        errors.append(f'{path}: project.languages must include at least one language')
    if not primary_language:
        errors.append(f'{path}: project.primary_language is required')
    elif primary_language and languages and primary_language not in languages:
        errors.append(f'{path}: project.primary_language must exist in project.languages')

    standards_profile = str(execution.get('standards_profile', '')).strip().lower()
    if standards_profile not in {'opt_in', 'required'}:
        errors.append(f'{path}: execution.standards_profile must be "opt_in" or "required"')

    recommend_preflight = execution.get('recommend_preflight')
    if not isinstance(recommend_preflight, bool):
        errors.append(f'{path}: execution.recommend_preflight must be true or false')

    language_tables = stack_data.get('language') or {}
    for language in languages:
        language_config = language_tables.get(language)
        if not isinstance(language_config, dict):
            errors.append(f'{path}: missing [language.{language}] table')
            continue
        for required in ('test_command', 'coverage_command', 'type_check_command', 'lint_command'):
            if _is_incomplete_value(str(language_config.get(required, '')).strip()):
                errors.append(f'{path}: language.{language}.{required} is required')

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
            errors.extend(_validate_stack_v2(stack_data, stack_toml))
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


def _resolve_languages(stack: ProjectStack, tooling: dict[str, LanguageTooling]) -> tuple[str, list[str]]:
    detected_languages = sorted(tooling.keys())
    configured_languages = [v.strip() for v in (stack.languages or []) if v.strip()]
    if not configured_languages and stack.language:
        configured_languages = [stack.language.strip()]
    primary_language = configured_languages[0] if configured_languages else ''

    if configured_languages:
        merged: list[str] = []
        for language in configured_languages + detected_languages:
            if language not in merged:
                merged.append(language)
        languages = merged
        primary_language = primary_language or languages[0]
    elif primary_language and primary_language not in detected_languages:
        languages = [primary_language, *detected_languages]
    elif primary_language:
        languages = [primary_language, *[lang for lang in detected_languages if lang != primary_language]]
    elif detected_languages:
        primary_language = detected_languages[0]
        languages = detected_languages
    else:
        languages = []

    return primary_language, languages


def render_stack_toml(stack: ProjectStack, tooling: dict[str, LanguageTooling]) -> str:
    primary_language, languages = _resolve_languages(stack, tooling)

    lines = [
        f'schema_version = {STACK_SCHEMA_VERSION}',
        '',
        '[project]',
        f'primary_language = {_toml_quote(primary_language)}',
        f'languages = {_toml_array(languages)}',
        '',
        '[execution]',
        'standards_profile = "opt_in"',
        'recommend_preflight = true',
        '',
    ]

    for language in languages:
        language_tooling = tooling.get(language)
        lines.extend(
            [
                f'[language.{language}]',
                f'runtime_version = {_toml_quote(stack.runtime_version if language == primary_language and stack.runtime_version else "")}',
                f'package_manager = {_toml_quote(stack.package_manager if language == primary_language and stack.package_manager else "")}',
                f'backend_framework = {_toml_quote(stack.backend_framework if language == primary_language and stack.backend_framework else "")}',
                f'frontend_framework = {_toml_quote(stack.frontend_framework if language == primary_language and stack.frontend_framework else "")}',
                f'database = {_toml_quote(stack.database if language == primary_language and stack.database else "")}',
                f'api_style = {_toml_quote(stack.api_style if language == primary_language and stack.api_style else "")}',
                f'architecture = {_toml_quote(stack.architecture if language == primary_language and stack.architecture else "")}',
                f'async_runtime = {str(bool(stack.async_runtime) if language == primary_language and stack.async_runtime is not None else False).lower()}',
                f'type_checker = {_toml_quote(language_tooling.checker if language_tooling and language_tooling.checker else "")}',
                f'test_runner = {_toml_quote(language_tooling.test_runner if language_tooling else "")}',
                f'test_command = {_toml_quote(language_tooling.test_command if language_tooling else "")}',
                f'coverage_command = {_toml_quote(language_tooling.coverage_command if language_tooling else "")}',
                f'type_check_command = {_toml_quote(language_tooling.check_command if language_tooling else "")}',
                f'lint_command = {_toml_quote(language_tooling.lint_command if language_tooling else "")}',
                '',
            ]
        )

    return '\n'.join(lines)


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
        stack_toml.write_text(render_stack_toml(stack, tooling), encoding='utf-8')
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

    return written
