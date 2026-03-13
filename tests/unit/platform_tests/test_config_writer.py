from pathlib import Path

from src.platform.config_writer import format_language_md, format_stack_md, write_config_files
from src.platform.models import LanguageTooling, ProjectStack


class TestFormatStackMd:
    def test_full_stack(self) -> None:
        stack = ProjectStack(
            language='python',
            runtime_version='3.13',
            backend_framework='fastapi',
            package_manager='uv',
            async_runtime=True,
            frontend_framework='htmx',
            css_framework='tailwindcss',
            ui_components='daisyui',
            database='postgresql',
            architecture='monolith',
            api_style='rest',
        )
        result = format_stack_md(stack)
        assert '# Project Stack' in result
        assert '## Languages' in result
        assert 'python 3.13' in result
        assert '## Backend' in result
        assert 'Framework: fastapi' in result
        assert 'Package Manager: uv' in result
        assert 'Async: Yes' in result
        assert '## Frontend' in result
        assert 'Framework: htmx' in result
        assert 'CSS: tailwindcss' in result
        assert 'Components: daisyui' in result
        assert '## Database' in result
        assert 'postgresql' in result
        assert '## Architecture' in result
        assert 'monolith' in result
        assert 'REST API' in result

    def test_partial_stack(self) -> None:
        stack = ProjectStack(language='python', package_manager='uv')
        result = format_stack_md(stack)
        assert '## Languages' in result
        assert 'python' in result.lower()
        assert '## Backend' in result
        assert 'Package Manager: uv' in result
        assert '## Frontend' not in result
        assert '## Database' not in result

    def test_empty_stack(self) -> None:
        stack = ProjectStack()
        result = format_stack_md(stack)
        assert '# Project Stack' in result
        assert '## Languages' not in result


class TestFormatLanguageMd:
    def test_python_with_all_commands(self) -> None:
        tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest --tb=short -v',
            coverage_command='pytest --cov --cov-report=term-missing --tb=short',
            checker='mypy',
            check_command='mypy src/ --exclude tests/',
            linter='ruff',
            lint_command='ruff check src/ tests/',
        )
        result = format_language_md('python', tooling)
        assert '# Python' in result
        assert '## Commands' in result
        assert '- **Test**: `pytest --tb=short -v`' in result
        assert '- **Coverage**: `pytest --cov --cov-report=term-missing --tb=short`' in result
        assert '- **Type check**: `mypy src/ --exclude tests/`' in result
        assert '- **Lint**: `ruff check src/ tests/`' in result
        assert '## Testing' in result
        assert '## Coding Standards' in result
        assert 'snake_case' in result

    def test_includes_testing_section(self) -> None:
        tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='mypy',
            check_command='mypy .',
            linter='ruff',
            lint_command='ruff check .',
        )
        result = format_language_md('python', tooling)
        assert '## Testing' in result
        assert 'pytest' in result

    def test_includes_coding_standards(self) -> None:
        tooling = LanguageTooling(
            test_runner='vitest',
            test_command='npx vitest run',
            coverage_command='npx vitest run --coverage',
            checker='tsc',
            check_command='npx tsc --noEmit',
            linter='eslint',
            lint_command='npx eslint src/',
        )
        result = format_language_md('javascript', tooling)
        assert '## Coding Standards' in result
        assert 'camelCase' in result

    def test_no_type_checker(self) -> None:
        tooling = LanguageTooling(
            test_runner='pytest',
            test_command='pytest',
            coverage_command='pytest --cov',
            checker='',
            check_command='',
            linter='ruff',
            lint_command='ruff check .',
        )
        result = format_language_md('python', tooling)
        assert '- **Type check**: none' in result


class TestWriteConfigFiles:
    def test_creates_directory_and_files(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        tooling = {
            'python': LanguageTooling(
                test_runner='pytest',
                test_command='pytest --tb=short -v',
                coverage_command='pytest --cov',
                checker='mypy',
                check_command='mypy src/',
                linter='ruff',
                lint_command='ruff check .',
            )
        }
        written = write_config_files(tmp_path, stack, tooling)

        assert len(written) == 2
        config_dir = tmp_path / '.respec-ai' / 'config'
        assert config_dir.exists()
        assert (config_dir / 'stack.md').exists()
        assert (config_dir / 'python.md').exists()

    def test_skips_existing_files(self, tmp_path: Path) -> None:
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
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)
        (config_dir / 'stack.md').write_text('existing content')

        written = write_config_files(tmp_path, stack, tooling)

        assert len(written) == 1
        assert written[0].name == 'python.md'
        assert (config_dir / 'stack.md').read_text() == 'existing content'

    def test_empty_tooling(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python')
        written = write_config_files(tmp_path, stack, {})

        assert len(written) == 1
        assert written[0].name == 'stack.md'
