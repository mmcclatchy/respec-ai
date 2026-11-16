import tomllib
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.markup import escape

from src.cli.ui.console import print_error
from src.platform.standards_config import load_toml_file
from src.utils.materializers import language_authoring_notes


NO_DECLARED_LANGUAGES_NOTE = (
    'No languages are declared in `.respec-ai/config/stack.toml` (`[project].languages`), so no'
    ' language-specific authoring notes apply. Write Skeleton Index and Test List entries in the'
    ' notation the phase template shows.'
)


def add_arguments(parser: ArgumentParser) -> None:
    pass


def run(args: Namespace) -> int:
    stack_toml = Path.cwd() / '.respec-ai' / 'config' / 'stack.toml'
    try:
        stack_data = load_toml_file(stack_toml)
    except (FileNotFoundError, NotADirectoryError):
        print(NO_DECLARED_LANGUAGES_NOTE)
        return 0
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as e:
        print_error(f'Could not read .respec-ai/config/stack.toml: {escape(str(e))}')
        return 1

    project = stack_data.get('project') or {}
    languages = [str(v).strip() for v in project.get('languages', []) if str(v).strip()]
    if not languages:
        print(NO_DECLARED_LANGUAGES_NOTE)
        return 0

    print(language_authoring_notes(languages))
    return 0
