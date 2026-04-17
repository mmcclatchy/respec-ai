from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack
from src.platform.standards_config import (
    available_languages,
    build_language_defaults,
    render_language_toml,
    validate_project_config,
    write_project_config_files,
)


def test_write_project_config_files_creates_canonical_toml(tmp_path: Path) -> None:
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
    assert len(written) == 3


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


def test_write_project_config_files_is_idempotent_when_files_exist(tmp_path: Path) -> None:
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
    second_write = write_project_config_files(tmp_path, stack, tooling)
    assert second_write == []


def test_language_defaults_have_starter_commands_and_rules() -> None:
    for language in available_languages():
        defaults = build_language_defaults(language)
        commands = defaults.get('commands', {})
        rules = defaults.get('rules', {})

        if language == 'universal':
            assert commands == {}
        else:
            for key in ('test', 'coverage', 'type_check', 'lint'):
                assert str(commands.get(key, '')).strip()

        for section in ('naming', 'imports', 'type_system', 'documentation', 'error_handling', 'code_structure'):
            values = [str(v).strip() for v in rules.get(section, []) if str(v).strip()]
            assert values


def test_universal_render_omits_commands_section() -> None:
    rendered = render_language_toml(build_language_defaults('universal'))
    assert '[commands]' not in rendered
    assert '[testing]' not in rendered
