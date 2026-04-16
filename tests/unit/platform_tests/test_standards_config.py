from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack
from src.platform.standards_config import render_markdown_mirrors, validate_project_config, write_project_config_files


def test_write_project_config_files_creates_toml_and_markdown(tmp_path: Path) -> None:
    stack = ProjectStack(language='python', backend_framework='fastapi', package_manager='uv')
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

    written = write_project_config_files(tmp_path, stack, tooling)

    config_dir = tmp_path / '.respec-ai' / 'config'
    assert (config_dir / 'stack.toml').exists()
    assert (config_dir / 'standards' / 'universal.toml').exists()
    assert (config_dir / 'standards' / 'python.toml').exists()
    assert (config_dir / 'stack.md').exists()
    assert (config_dir / 'universal.md').exists()
    assert (config_dir / 'python.md').exists()
    assert len(written) >= 6


def test_validate_project_config_passes_for_generated_defaults(tmp_path: Path) -> None:
    stack = ProjectStack(language='python', backend_framework='fastapi', package_manager='uv')
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
    write_project_config_files(tmp_path, stack, tooling)
    errors = validate_project_config(tmp_path)
    assert errors == []


def test_render_markdown_mirrors_rewrites_mirrors_from_toml(tmp_path: Path) -> None:
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
    write_project_config_files(tmp_path, stack, tooling)
    stack_md = tmp_path / '.respec-ai' / 'config' / 'stack.md'
    stack_md.write_text('stale', encoding='utf-8')

    rendered = render_markdown_mirrors(tmp_path)

    assert stack_md.read_text(encoding='utf-8').startswith('# Project Stack')
    assert stack_md in rendered
