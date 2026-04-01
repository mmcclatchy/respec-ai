from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.standards.upgrader import find_config_files, upgrade_config_file
from src.cli.ui.console import print_error, print_info, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--upgrade',
        action='store_true',
        help='Upgrade config files to use MANDATORY protocol blocks',
    )
    parser.add_argument(
        'language',
        nargs='?',
        default=None,
        help='Specific language config to upgrade (e.g., python, universal)',
    )


def run(args: Namespace) -> int:
    if not args.upgrade:
        print_error('Please specify an action: --upgrade')
        print_info('Usage: respec-ai standards --upgrade [language]')
        return 1

    return _run_upgrade(args)


def _run_upgrade(args: Namespace) -> int:
    project_path = Path.cwd()
    config_dir = project_path / '.respec-ai' / 'config'

    if not config_dir.exists():
        print_error('No config directory found at .respec-ai/config/')
        print_info('Run: respec-ai init to generate config files')
        return 1

    files = find_config_files(project_path, args.language)

    if not files:
        if args.language:
            print_error(f'Config file not found: .respec-ai/config/{args.language}.md')
        else:
            print_warning('No config files found to upgrade (excluding stack.md)')
        return 1

    upgraded_count = 0
    for path in files:
        changed = upgrade_config_file(path)
        if changed:
            print_success(f'Upgraded: {path.relative_to(project_path)}')
            upgraded_count += 1
        else:
            print_info(f'Already up to date: {path.relative_to(project_path)}')

    if upgraded_count > 0:
        print_success(f'Upgraded {upgraded_count} config file(s) with MANDATORY protocol blocks')
    else:
        print_info('All config files already use MANDATORY protocol blocks')

    return 0
