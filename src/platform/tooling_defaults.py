import json
import tomllib
from pathlib import Path
from typing import Any

from src.platform.models import LanguageStackProfile, LanguageTooling, ProjectStack


TOOLING_DEFAULTS: dict[str, LanguageTooling] = {
    'python': LanguageTooling(
        test_runner='pytest',
        test_command='pytest --tb=short -v',
        coverage_command='pytest --cov --cov-report=term-missing --tb=short',
        checker='mypy',
        check_command='mypy src/ --exclude tests/',
        linter='ruff',
        lint_command='ruff check src/ tests/',
    ),
    'javascript': LanguageTooling(
        test_runner='vitest',
        test_command='npx vitest run',
        coverage_command='npx vitest run --coverage',
        checker='tsc',
        check_command='npx tsc --noEmit',
        linter='eslint',
        lint_command='npx eslint src/',
    ),
    'go': LanguageTooling(
        test_runner='go test',
        test_command='go test ./...',
        coverage_command='go test -cover ./...',
        checker='go vet',
        check_command='go vet ./...',
        linter='golangci-lint',
        lint_command='golangci-lint run',
    ),
    'rust': LanguageTooling(
        test_runner='cargo test',
        test_command='cargo test',
        coverage_command='cargo tarpaulin',
        checker='cargo check',
        check_command='cargo check --verbose',
        linter='clippy',
        lint_command='cargo clippy -- -D warnings',
    ),
}

BUILD_FILE_TO_LANGUAGE: dict[str, str] = {
    'pyproject.toml': 'python',
    'requirements.txt': 'python',
    'package.json': 'javascript',
    'go.mod': 'go',
    'Cargo.toml': 'rust',
}


def detect_project_tooling(project_path: Path) -> dict[str, LanguageTooling]:
    detected: dict[str, LanguageTooling] = {}
    for build_file, language in BUILD_FILE_TO_LANGUAGE.items():
        if (project_path / build_file).exists() and language not in detected:
            if language in TOOLING_DEFAULTS:
                detected[language] = TOOLING_DEFAULTS[language]
    if (project_path / 'package.json').exists() and (project_path / 'tsconfig.json').exists():
        detected.pop('javascript', None)
        # TypeScript inherits JavaScript tool defaults and is promoted at detection time.
        detected['typescript'] = LanguageTooling.model_validate(TOOLING_DEFAULTS['javascript'].model_dump())
    return detected


# Per-language type-checker override options (F25). Keying by language, rather than a single
# Python-only table, is what lets a TypeScript project's configured type_checker survive instead
# of being silently dropped (B5).
TYPE_CHECKER_COMMANDS: dict[str, dict[str, str]] = {
    'python': {
        'ty': 'ty check',
        'mypy': 'mypy src/ --exclude tests/',
        'pyright': 'pyright',
        'pytype': 'pytype src/',
    },
    'typescript': {
        'tsc': 'npx tsc --noEmit',
    },
    'javascript': {
        'tsc': 'npx tsc --noEmit',
    },
}


def apply_stack_to_tooling(tooling: dict[str, LanguageTooling], stack: ProjectStack) -> dict[str, LanguageTooling]:
    updated_tooling = dict(tooling)

    for language, profile in stack.language_stack.items():
        if not profile.type_checker or language not in updated_tooling:
            continue

        check_commands = TYPE_CHECKER_COMMANDS.get(language, {})
        type_checker = profile.type_checker
        if type_checker not in check_commands:
            continue

        current = updated_tooling[language]
        updated_tooling[language] = LanguageTooling(
            test_runner=current.test_runner,
            test_command=current.test_command,
            coverage_command=current.coverage_command,
            checker=type_checker,
            check_command=check_commands[type_checker],
            linter=current.linter,
            lint_command=current.lint_command,
        )

    return updated_tooling


PYTHON_FRAMEWORKS: dict[str, str] = {
    'fastapi': 'fastapi',
    'fastmcp': 'fastmcp',
    'flask': 'flask',
    'django': 'django',
    'starlette': 'starlette',
    'sanic': 'sanic',
    'litestar': 'litestar',
}

JS_BACKEND_FRAMEWORKS: dict[str, str] = {
    'express': 'express',
    'fastify': 'fastify',
    'hono': 'hono',
}

JS_FRONTEND_FRAMEWORKS: dict[str, str] = {
    'react': 'react',
    'react-dom': 'react',
    'next': 'next',
    'vue': 'vue',
    'nuxt': 'nuxt',
    'svelte': 'svelte',
    '@angular/core': 'angular',
}

REST_FRAMEWORKS: set[str] = {
    'fastapi',
    'flask',
    'django',
    'express',
    'fastify',
    'hono',
    'starlette',
    'litestar',
    'sanic',
}

MCP_FRAMEWORKS: set[str] = {
    'fastmcp',
}

ASYNC_FRAMEWORKS: set[str] = {
    'fastapi',
    'fastmcp',
    'starlette',
    'litestar',
    'sanic',
    'express',
    'fastify',
    'hono',
}


def _detect_from_pyproject(pyproject_path: Path) -> tuple[dict[str, Any], LanguageStackProfile]:
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
    except Exception:
        return {}, LanguageStackProfile()

    package_manager = 'pip'
    if 'tool' in data and 'uv' in data['tool']:
        package_manager = 'uv'

    runtime_version: str | None = None
    requires_python = data.get('project', {}).get('requires-python')
    if requires_python:
        cleaned = requires_python.replace('>=', '').replace('>', '').replace('~=', '').replace('==', '').strip()
        if cleaned:
            runtime_version = cleaned.split(',')[0].strip()

    backend_framework: str | None = None
    deps = data.get('project', {}).get('dependencies', [])
    for dep in deps:
        dep_name = dep.split('>=')[0].split('==')[0].split('<')[0].split('[')[0].strip().lower()
        if dep_name in PYTHON_FRAMEWORKS:
            backend_framework = PYTHON_FRAMEWORKS[dep_name]
            break

    api_style: str | None = None
    if backend_framework:
        if backend_framework in MCP_FRAMEWORKS:
            api_style = 'mcp'
        elif backend_framework in REST_FRAMEWORKS:
            api_style = 'rest'

    async_runtime: bool | None = None
    if backend_framework:
        async_runtime = backend_framework in ASYNC_FRAMEWORKS

    type_checker: str | None = None
    if 'tool' in data:
        if 'ty' in data['tool']:
            type_checker = 'ty'
        elif 'mypy' in data['tool']:
            type_checker = 'mypy'
        elif 'pyright' in data['tool']:
            type_checker = 'pyright'

    flat_updates: dict[str, Any] = {
        'backend_framework': backend_framework,
        'api_style': api_style,
        'async_runtime': async_runtime,
    }
    profile = LanguageStackProfile(
        package_manager=package_manager,
        runtime_version=runtime_version,
        type_checker=type_checker,
    )
    return flat_updates, profile


def _detect_from_package_json(
    package_json_path: Path, project_path: Path
) -> tuple[str, dict[str, Any], LanguageStackProfile]:
    try:
        data = json.loads(package_json_path.read_text(encoding='utf-8'))
    except Exception:
        return 'javascript', {}, LanguageStackProfile()

    language = 'javascript'
    if (project_path / 'tsconfig.json').exists():
        language = 'typescript'

    package_manager = 'npm'
    if (project_path / 'yarn.lock').exists():
        package_manager = 'yarn'
    elif (project_path / 'pnpm-lock.yaml').exists():
        package_manager = 'pnpm'

    runtime_version: str | None = None
    engines_node = data.get('engines', {}).get('node')
    if engines_node:
        cleaned = engines_node.replace('>=', '').replace('>', '').replace('~', '').replace('^', '').strip()
        if cleaned:
            runtime_version = cleaned.split(' ')[0].strip()

    backend_framework: str | None = None
    frontend_framework: str | None = None
    all_deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
    for dep_name in all_deps:
        if not backend_framework and dep_name in JS_BACKEND_FRAMEWORKS:
            backend_framework = JS_BACKEND_FRAMEWORKS[dep_name]
        if not frontend_framework and dep_name in JS_FRONTEND_FRAMEWORKS:
            frontend_framework = JS_FRONTEND_FRAMEWORKS[dep_name]

    api_style: str | None = None
    if backend_framework:
        if backend_framework in MCP_FRAMEWORKS:
            api_style = 'mcp'
        elif backend_framework in REST_FRAMEWORKS:
            api_style = 'rest'

    async_runtime: bool | None = None
    if backend_framework:
        async_runtime = backend_framework in ASYNC_FRAMEWORKS

    flat_updates: dict[str, Any] = {
        'backend_framework': backend_framework,
        'api_style': api_style,
        'async_runtime': async_runtime,
    }
    profile = LanguageStackProfile(
        frontend_framework=frontend_framework,
        package_manager=package_manager,
        runtime_version=runtime_version,
    )
    return language, flat_updates, profile


def detect_project_stack(project_path: Path) -> ProjectStack:
    detected_tooling = detect_project_tooling(project_path)
    detected_languages = list(detected_tooling.keys())
    if not detected_languages:
        return ProjectStack()

    pyproject = project_path / 'pyproject.toml'
    package_json = project_path / 'package.json'
    go_mod = project_path / 'go.mod'
    cargo_toml = project_path / 'Cargo.toml'

    flat_updates: dict[str, Any] = {}
    language_stack: dict[str, LanguageStackProfile] = {}

    # Every matching detector runs -- a repo with both pyproject.toml and package.json gets
    # both halves (B2). The elif chain this replaced silently dropped the frontend half of
    # every polyglot project (F2).
    if pyproject.exists():
        py_flat, py_profile = _detect_from_pyproject(pyproject)
        for key, value in py_flat.items():
            if value is not None:
                flat_updates.setdefault(key, value)
        language_stack['python'] = py_profile

    if package_json.exists():
        js_language, js_flat, js_profile = _detect_from_package_json(package_json, project_path)
        for key, value in js_flat.items():
            if value is not None:
                flat_updates.setdefault(key, value)
        language_stack[js_language] = js_profile

    if go_mod.exists() and 'go' not in language_stack:
        language_stack['go'] = LanguageStackProfile(package_manager='go modules')

    if cargo_toml.exists() and 'rust' not in language_stack:
        language_stack['rust'] = LanguageStackProfile(package_manager='cargo')

    primary_language = detected_languages[0]
    return ProjectStack(
        language=primary_language,
        languages=detected_languages,
        language_stack=language_stack,
        **flat_updates,
    )
