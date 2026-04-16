from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.ui.console import print_error, print_info, print_success, print_warning
from src.platform.standards_config import (
    available_languages,
    build_language_template,
    render_language_toml,
    render_markdown_mirrors,
    validate_project_config,
)


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='standards_command', required=True)

    init_parser = subparsers.add_parser(
        'init',
        help='Initialize standards TOML template files',
    )
    init_parser.add_argument(
        '--language',
        help='Language to initialize (default: all known languages + universal)',
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
    subparsers.add_parser(
        'render',
        help='Render markdown mirror files from canonical TOML',
    )


def run(args: Namespace) -> int:
    command = args.standards_command
    if command == 'init':
        return _run_init(args)
    if command == 'validate':
        return _run_validate()
    if command == 'render':
        return _run_render()
    print_error(f'Unknown standards command: {command}')
    return 1


def _run_init(args: Namespace) -> int:
    project_path = Path.cwd()
    config_dir = project_path / '.respec-ai' / 'config'
    standards_dir = config_dir / 'standards'
    standards_dir.mkdir(parents=True, exist_ok=True)

    languages = available_languages()
    if args.language:
        requested = args.language.strip().lower()
        if requested not in languages:
            print_error(f'Unsupported language: {requested}')
            print_info(f'Available languages: {", ".join(languages)}')
            return 1
        target_languages = [requested]
    else:
        target_languages = languages

    written = 0
    for language in target_languages:
        target = standards_dir / f'{language}.toml'
        if target.exists() and not args.force:
            print_info(f'Exists (skipped): {target.relative_to(project_path)}')
            continue

        template = build_language_template(language)
        target.write_text(render_language_toml(template), encoding='utf-8')
        print_success(f'Wrote template: {target.relative_to(project_path)}')
        written += 1

    # Ensure mirrors are refreshed from canonical files after init.
    rendered = render_markdown_mirrors(project_path)
    if rendered:
        print_info(f'Rendered {len(rendered)} markdown mirror file(s)')

    if written == 0:
        print_warning('No files created (all targets existed)')
        return 0

    print_success(f'Initialized {written} standards template file(s)')
    print_info('Run `respec-ai standards validate` after filling template placeholders.')
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


def _run_render() -> int:
    project_path = Path.cwd()
    errors = validate_project_config(project_path)
    if errors:
        print_error('Cannot render markdown mirrors: standards config is invalid')
        for error in errors:
            print_error(f'- {error}')
        return 1

    rendered = render_markdown_mirrors(project_path)
    if not rendered:
        print_warning('No markdown mirrors rendered (no canonical TOML files found)')
        return 1

    for path in rendered:
        print_success(f'Rendered: {path.relative_to(project_path)}')
    return 0
