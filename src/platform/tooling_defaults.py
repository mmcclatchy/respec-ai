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
    'typescript': LanguageTooling(
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
        detected['typescript'] = TOOLING_DEFAULTS['typescript']
    return detected


def _primary_language(stack: ProjectStack) -> str | None:
    if stack.languages:
        return stack.languages[0]
    return stack.language


def apply_stack_to_tooling(tooling: dict[str, LanguageTooling], stack: ProjectStack) -> dict[str, LanguageTooling]:
    primary_language = _primary_language(stack)
    if not stack.type_checker or not primary_language or primary_language not in tooling:
        return tooling

    updated_tooling = dict(tooling)
    language = primary_language

    if language == 'python' and language in updated_tooling:
        current = updated_tooling[language]
        type_checker = stack.type_checker

        check_commands = {
            'ty': 'ty check',
            'mypy': 'mypy src/ --exclude tests/',
            'pyright': 'pyright',
            'pytype': 'pytype src/',
        }

        if type_checker in check_commands:
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

    return ProjectStack(
        language='python',
        backend_framework=backend_framework,
        package_manager=package_manager,
        runtime_version=runtime_version,
        api_style=api_style,
        async_runtime=async_runtime,
        type_checker=type_checker,
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
    if backend_framework:
        if backend_framework in MCP_FRAMEWORKS:
            api_style = 'mcp'
        elif backend_framework in REST_FRAMEWORKS:
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
    detected_tooling = detect_project_tooling(project_path)
    detected_languages = list(detected_tooling.keys())
    if not detected_languages:
        return ProjectStack()

    pyproject = project_path / 'pyproject.toml'
    package_json = project_path / 'package.json'
    go_mod = project_path / 'go.mod'
    cargo_toml = project_path / 'Cargo.toml'

    if pyproject.exists():
        base_stack = _detect_from_pyproject(pyproject)
    elif package_json.exists():
        base_stack = _detect_from_package_json(package_json, project_path)
    elif go_mod.exists():
        base_stack = ProjectStack(language='go', package_manager='go modules')
    elif cargo_toml.exists():
        base_stack = ProjectStack(language='rust', package_manager='cargo')
    else:
        base_stack = ProjectStack()

    primary_language = detected_languages[0]
    return base_stack.model_copy(update={'language': primary_language, 'languages': detected_languages})
