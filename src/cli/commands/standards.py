from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.ui.console import print_error, print_info, print_success, print_warning
from src.platform.standards_config import (
    available_languages,
    build_language_defaults,
    render_language_toml,
    validate_project_config,
)


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='standards_command', required=True)

    init_parser = subparsers.add_parser(
        'init',
        help='Initialize standards TOML files for one or more languages',
    )
    init_parser.add_argument(
        'languages',
        nargs='+',
        help='Space-delimited languages to initialize (e.g., python typescript)',
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing TOML files',
    )

    subparsers.add_parser(
        'validate',
        help='Validate canonical standards TOML files',
    )


def run(args: Namespace) -> int:
    command = args.standards_command
    if command == 'init':
        return _run_init(args)
    if command == 'validate':
        return _run_validate()
    print_error(f'Unknown standards command: {command}')
    return 1


def _run_init(args: Namespace) -> int:
    project_path = Path.cwd()
    config_dir = project_path / '.respec-ai' / 'config'
    standards_dir = config_dir / 'standards'
    standards_dir.mkdir(parents=True, exist_ok=True)

    supported_languages = set(available_languages())
    target_languages: list[str] = []
    for language in args.languages:
        normalized = str(language).strip().lower()
        if normalized and normalized not in target_languages:
            target_languages.append(normalized)

    unsupported = [language for language in target_languages if language not in supported_languages]
    if unsupported:
        print_error(f'Unsupported language(s): {", ".join(unsupported)}')
        print_info(f'Available languages: {", ".join(sorted(supported_languages))}')
        return 1

    written = 0
    for language in target_languages:
        target = standards_dir / f'{language}.toml'
        if target.exists() and not args.force:
            print_info(f'Exists (skipped): {target.relative_to(project_path)}')
            continue

        template = build_language_defaults(language)
        target.write_text(render_language_toml(template), encoding='utf-8')
        print_success(f'Wrote standards: {target.relative_to(project_path)}')
        written += 1

    if written == 0:
        print_warning('No files created (all targets existed)')
        return 0

    print_success(f'Initialized {written} standards file(s)')
    print_info('Run `respec-ai standards validate` to verify generated defaults.')
    return 0


def _run_validate() -> int:
    errors = validate_project_config(Path.cwd())
    if not errors:
        print_success('Standards config validation passed')
        return 0

    print_error('Standards config validation failed')
    for error in errors:
        print_error(f'- {error}')
    return 1
