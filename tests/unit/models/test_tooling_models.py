import pytest
from pydantic import ValidationError

from src.platform.models import LanguageTooling, ProjectToolingConfig


class TestLanguageTooling:
    def test_valid_language_tooling(self) -> None:
        tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest --tb=short -v',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy src/',
            linter='ruff',
            lint_command='ruff check src/',
        )
        assert tooling.test_runner == 'pytest'
        assert tooling.checker == 'mypy'

    def test_all_fields_required(self) -> None:
        with pytest.raises(ValidationError):
            LanguageTooling(  # type: ignore[call-arg]  # ty: ignore[missing-argument]
                test_runner='pytest',
                test_command='pytest',
            )

    def test_immutable(self) -> None:
        tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy src/',
            linter='ruff',
            lint_command='ruff check',
        )
        with pytest.raises(ValidationError):
            tooling.test_runner = 'vitest'

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            LanguageTooling(
                test_runner='pytest',
                test_command='pytest',
                coverage_command='pytest --cov',
                checker='mypy',
                check_command='mypy src/',
                linter='ruff',
                lint_command='ruff check',
                extra_field='not_allowed',
            )


class TestProjectToolingConfig:
    def test_empty_tooling(self) -> None:
        config = ProjectToolingConfig()
        assert config.tooling == {}

    def test_populated_tooling(self) -> None:
        python_tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest --tb=short -v',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy src/',
            linter='ruff',
            lint_command='ruff check src/',
        )
        config = ProjectToolingConfig(tooling={'python': python_tooling})
        assert 'python' in config.tooling
        assert config.tooling['python'].test_runner == 'pytest'

    def test_multiple_languages(self) -> None:
        python = LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy src/',
            linter='ruff',
            lint_command='ruff check',
        )
        js = LanguageTooling(
            test_runner='vitest',
            test_command='npx vitest run',
            coverage_command='npx vitest run --coverage',
            checker='tsc',
            check_command='npx tsc --noEmit',
            linter='eslint',
            lint_command='npx eslint src/',
        )
        config = ProjectToolingConfig(tooling={'python': python, 'javascript': js})
        assert len(config.tooling) == 2
        assert config.tooling['javascript'].checker == 'tsc'
