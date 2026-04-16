from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack
from src.platform.standards_config import (
    build_language_defaults,
    render_language_markdown_from_toml,
    render_stack_markdown_from_toml,
    write_project_config_files,
)


def format_stack_md(stack: ProjectStack) -> str:
    stack_data = {
        'project': {'language': stack.language or ''},
        'stack': {
            'backend_framework': stack.backend_framework or '',
            'frontend_framework': stack.frontend_framework or '',
            'package_manager': stack.package_manager or '',
            'runtime_version': stack.runtime_version or '',
            'database': stack.database or '',
            'api_style': stack.api_style or '',
            'architecture': stack.architecture or '',
            'type_checker': stack.type_checker or '',
            'css_framework': stack.css_framework or '',
            'ui_components': stack.ui_components or '',
            'async_runtime': bool(stack.async_runtime),
        },
    }
    return render_stack_markdown_from_toml(stack_data)


def format_language_md(lang: str, tooling: LanguageTooling) -> str:
    language_data = build_language_defaults(lang, tooling)
    return render_language_markdown_from_toml(language_data)


def write_config_files(
    project_path: Path,
    stack: ProjectStack,
    tooling: dict[str, LanguageTooling],
) -> list[Path]:
    return write_project_config_files(project_path, stack, tooling)
