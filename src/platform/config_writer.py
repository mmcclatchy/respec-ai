from pathlib import Path

from src.platform.models import LanguageTooling, ProjectStack
from src.platform.standards_config import write_project_config_files


def write_config_files(
    project_path: Path,
    stack: ProjectStack,
    tooling: dict[str, LanguageTooling],
) -> list[Path]:
    return write_project_config_files(project_path, stack, tooling)
