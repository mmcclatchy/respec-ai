import json
from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack


DATA_DIR = Path(__file__).parent / 'data'

UNIVERSAL_STANDARDS = """# Universal Coding Standards

## Security

### Secrets
- No hardcoded secrets (API keys, passwords, tokens, connection strings) in source code
- No credentials in source code — use environment variables or config references
- Test fixtures with obviously fake values are acceptable

## Code Separation

### Production
- No test logic in production code
- No production logic in test files

## Imports

### Organization
- No inline imports — all imports at file top
- Exception: circular dependency resolution

## Error Handling

### Patterns
- Fail fast — validate inputs early, reject invalid state immediately
- Use specific exceptions — no bare except or catch-all Exception handlers
- Provide meaningful error messages — include what went wrong and what was expected
- No silent failures — do not swallow exceptions without logging or re-raising

## Logging

### Hygiene
- No PII (personally identifiable information) in log output
- No secrets, tokens, or credentials in log messages
- Include context in log messages — what operation, what entity, what outcome

## Dependencies

### Management
- Prefer well-maintained libraries — last commit within 6 months, good documentation
- Document why a dependency was chosen over alternatives
- Pin versions for reproducible builds
"""

CODING_STANDARDS_FIELDS: dict[str, str] = {
    'naming': 'Naming',
    'imports': 'Imports',
    'type_system': 'Type System',
    'documentation': 'Documentation',
    'error_handling': 'Error Handling',
    'code_structure': 'Code Structure',
}


def _load_language_standards() -> dict[str, dict]:
    standards_path = DATA_DIR / 'language_standards.json'
    return json.loads(standards_path.read_text(encoding='utf-8'))


def _render_coding_standards(data: dict) -> str:
    sections: list[str] = []
    for field, header in CODING_STANDARDS_FIELDS.items():
        rules = data.get(field, [])
        if rules:
            bullets = '\n'.join(f'- {r}' for r in rules)
            sections.append(f'### {header}\n{bullets}')

    if not sections:
        return ''

    return '## Coding Standards\n\n' + '\n\n'.join(sections)


def _render_testing(data: dict) -> str:
    testing = data.get('testing')
    if not testing:
        return ''

    lines = [
        f'- Framework: {testing["framework"]}',
        f'- Location: {testing["location"]}',
        f'- Naming: {testing["naming"]}',
    ]
    for extra in testing.get('extras', []):
        lines.append(f'- {extra}')

    return '## Testing\n\n' + '\n'.join(lines)


def format_stack_md(stack: ProjectStack) -> str:
    lines = ['# Project Stack']

    if stack.language:
        lang_parts = [stack.language]
        if stack.runtime_version:
            lang_parts.append(stack.runtime_version)
        lines.extend(['', '## Languages', f'- {" ".join(lang_parts)}'])

    backend_lines: list[str] = []
    if stack.backend_framework:
        backend_lines.append(f'- Framework: {stack.backend_framework}')
    if stack.package_manager:
        backend_lines.append(f'- Package Manager: {stack.package_manager}')
    if stack.async_runtime is not None:
        backend_lines.append(f'- Async: {"Yes" if stack.async_runtime else "No"}')
    if backend_lines:
        lines.extend(['', '## Backend', *backend_lines])

    frontend_lines: list[str] = []
    if stack.frontend_framework:
        frontend_lines.append(f'- Framework: {stack.frontend_framework}')
    if stack.css_framework:
        frontend_lines.append(f'- CSS: {stack.css_framework}')
    if stack.ui_components:
        frontend_lines.append(f'- Components: {stack.ui_components}')
    if frontend_lines:
        lines.extend(['', '## Frontend', *frontend_lines])

    if stack.database:
        lines.extend(['', '## Database', f'- {stack.database}'])

    architecture_parts: list[str] = []
    if stack.architecture:
        architecture_parts.append(stack.architecture)
    if stack.api_style:
        architecture_parts.append(f'{stack.api_style.upper()} API')
    if architecture_parts:
        lines.extend(['', '## Architecture', f'- {", ".join(architecture_parts)}'])

    lines.append('')
    return '\n'.join(lines)


def format_language_md(lang: str, tooling: LanguageTooling) -> str:
    lines = [f'# {lang.title()}', '', '## Commands', '']
    lines.append(f'- **Test**: `{tooling.test_command}`')
    lines.append(f'- **Coverage**: `{tooling.coverage_command}`')
    if tooling.checker and tooling.check_command:
        lines.append(f'- **Type check**: `{tooling.check_command}`')
    else:
        lines.append('- **Type check**: none')
    lines.append(f'- **Lint**: `{tooling.lint_command}`')

    all_standards = _load_language_standards()
    lang_data = all_standards.get(lang, {})

    testing_md = _render_testing(lang_data)
    if testing_md:
        lines.extend(['', testing_md])
    else:
        lines.extend(['', f'## Testing\n\n- Framework: {tooling.test_runner}'])

    coding_md = _render_coding_standards(lang_data)
    if coding_md:
        lines.extend(['', coding_md])

    lines.append('')
    return '\n'.join(lines)


def write_config_files(
    project_path: Path,
    stack: ProjectStack,
    tooling: dict[str, LanguageTooling],
) -> list[Path]:
    config_dir = project_path / '.respec-ai' / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    universal_path = config_dir / 'universal.md'
    if not universal_path.exists():
        universal_path.write_text(UNIVERSAL_STANDARDS, encoding='utf-8')
        written.append(universal_path)

    stack_path = config_dir / 'stack.md'
    if not stack_path.exists():
        stack_path.write_text(format_stack_md(stack), encoding='utf-8')
        written.append(stack_path)

    for lang, lang_tooling in tooling.items():
        lang_path = config_dir / f'{lang}.md'
        if not lang_path.exists():
            lang_path.write_text(format_language_md(lang, lang_tooling), encoding='utf-8')
            written.append(lang_path)

    return written
