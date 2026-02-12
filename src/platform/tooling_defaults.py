from pathlib import Path

from src.platform.models import LanguageTooling


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
