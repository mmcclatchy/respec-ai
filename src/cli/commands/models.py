from argparse import ArgumentParser, Namespace

from src.cli.commands import codex_model, opencode_model
from src.cli.ui.console import print_error


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='models_command', required=True, help='Model configuration commands')

    opencode_parser = subparsers.add_parser(
        'opencode',
        help='Configure OpenCode reasoning/task model tiers',
    )
    opencode_model.add_arguments(opencode_parser)

    codex_parser = subparsers.add_parser(
        'codex',
        help='Configure Codex reasoning/task model tiers',
    )
    codex_model.add_arguments(codex_parser)


def run(args: Namespace) -> int:
    if args.models_command == 'opencode':
        return opencode_model.run(args)
    if args.models_command == 'codex':
        return codex_model.run(args)
    print_error(f'Unknown models command: {args.models_command}')
    return 1
