import json
import tomllib
from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack


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
    return detected


PYTHON_FRAMEWORKS: dict[str, str] = {
    'fastapi': 'fastapi',
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

ASYNC_FRAMEWORKS: set[str] = {
    'fastapi',
    'starlette',
    'litestar',
    'sanic',
    'express',
    'fastify',
    'hono',
}


def _detect_from_pyproject(pyproject_path: Path) -> ProjectStack:
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
    except Exception:
        return ProjectStack(language='python')

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
    if backend_framework and backend_framework in REST_FRAMEWORKS:
        api_style = 'rest'

    async_runtime: bool | None = None
    if backend_framework:
        async_runtime = backend_framework in ASYNC_FRAMEWORKS

    return ProjectStack(
        language='python',
        backend_framework=backend_framework,
        package_manager=package_manager,
        runtime_version=runtime_version,
        api_style=api_style,
        async_runtime=async_runtime,
    )


def _detect_from_package_json(package_json_path: Path, project_path: Path) -> ProjectStack:
    try:
        data = json.loads(package_json_path.read_text(encoding='utf-8'))
    except Exception:
        return ProjectStack(language='javascript')

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
    if backend_framework and backend_framework in REST_FRAMEWORKS:
        api_style = 'rest'

    async_runtime: bool | None = None
    if backend_framework:
        async_runtime = backend_framework in ASYNC_FRAMEWORKS

    return ProjectStack(
        language=language,
        backend_framework=backend_framework,
        frontend_framework=frontend_framework,
        package_manager=package_manager,
        runtime_version=runtime_version,
        api_style=api_style,
        async_runtime=async_runtime,
    )


def detect_project_stack(project_path: Path) -> ProjectStack:
    pyproject = project_path / 'pyproject.toml'
    if pyproject.exists():
        return _detect_from_pyproject(pyproject)

    package_json = project_path / 'package.json'
    if package_json.exists():
        return _detect_from_package_json(package_json, project_path)

    go_mod = project_path / 'go.mod'
    if go_mod.exists():
        return ProjectStack(language='go', package_manager='go modules')

    cargo_toml = project_path / 'Cargo.toml'
    if cargo_toml.exists():
        return ProjectStack(language='rust', package_manager='cargo')

    return ProjectStack()
