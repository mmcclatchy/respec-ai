from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack


UNIVERSAL_STANDARDS = """# Universal Coding Standards

## Security
- No hardcoded secrets (API keys, passwords, tokens, connection strings) in source code
- No credentials in source code — use environment variables or config references
- Test fixtures with obviously fake values are acceptable

## Code Separation
- No test logic in production code
- No production logic in test files

## Imports
- No inline imports — all imports at file top
- Exception: circular dependency resolution
"""


LANGUAGE_CODING_STANDARDS: dict[str, str] = {
    'python': """## Coding Standards

### Naming
- Variables/functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

### Imports
- Absolute imports only
- Group order: stdlib → third-party → local
- All at file top

### Type Hints
- Required on all function parameters and return values
- Use `X | None` not `Optional[X]`

### Documentation
- Docstrings: public APIs only
- Comments: non-obvious business logic only""",
    'javascript': """## Coding Standards

### Naming
- Variables/functions: camelCase
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

### Imports
- Named imports preferred over default
- Group order: stdlib → third-party → local

### Documentation
- JSDoc for public APIs only
- Comments: non-obvious business logic only""",
    'typescript': """## Coding Standards

### Naming
- Variables/functions: camelCase
- Classes/Interfaces: PascalCase
- Constants: UPPER_SNAKE_CASE

### Imports
- Named imports preferred over default
- Group order: stdlib → third-party → local

### Type Annotations
- Strict mode enabled
- Avoid `any` type

### Documentation
- JSDoc/TSDoc for public APIs only
- Comments: non-obvious business logic only""",
    'go': """## Coding Standards

### Naming
- Unexported: camelCase
- Exported: PascalCase
- Acronyms: all caps (e.g., HTTPServer)

### Imports
- Group order: stdlib → third-party → local
- Use goimports for formatting

### Documentation
- Package-level comments required
- Exported functions require doc comments""",
    'rust': """## Coding Standards

### Naming
- Variables/functions: snake_case
- Types/Traits: PascalCase
- Constants: UPPER_SNAKE_CASE

### Documentation
- `///` doc comments for public items
- `//!` for module-level documentation""",
}

LANGUAGE_TESTING_DEFAULTS: dict[str, str] = {
    'python': """## Testing

- Framework: pytest with pytest-mock
- Location: tests/ directory, mirrors src/ structure
- Naming: test_{function}_{scenario}
- Prefer integration tests over mocked unit tests for database operations""",
    'javascript': """## Testing

- Framework: vitest
- Location: tests/ or __tests__/ directories
- Naming: describe/it blocks with clear descriptions""",
    'typescript': """## Testing

- Framework: vitest
- Location: tests/ or __tests__/ directories
- Naming: describe/it blocks with clear descriptions""",
    'go': """## Testing

- Framework: testing (stdlib)
- Location: *_test.go files alongside source
- Naming: TestFunctionName_Scenario""",
    'rust': """## Testing

- Framework: cargo test (built-in)
- Location: #[cfg(test)] mod tests in source files
- Integration tests in tests/ directory""",
}


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

    testing = LANGUAGE_TESTING_DEFAULTS.get(lang, f'## Testing\n\n- Framework: {tooling.test_runner}')
    lines.extend(['', testing])

    coding_standards = LANGUAGE_CODING_STANDARDS.get(lang)
    if coding_standards:
        lines.extend(['', coding_standards])

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
