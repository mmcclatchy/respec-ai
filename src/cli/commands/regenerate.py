import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn
from src.cli.config.package_info import get_package_version
from src.platform.template_generator import generate_templates
from src.cli.ui.console import console, print_error, print_info, print_success, print_warning
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate templates even if version is current',
    )


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            print_error('RespecAI is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        config = json.loads(config_path.read_text(encoding='utf-8'))
        current_version = config.get('version', 'unknown')
        package_version = get_package_version()
        platform = config.get('platform')

        if not platform:
            print_error('Platform not set in config')
            print_warning('Delete .respec-ai/config.json and run: respec-ai init')
            return 1

        if current_version == package_version and not args.force:
            print_info(f'Templates are already up to date (v{package_version})')
            print_info('Use --force to regenerate anyway')
            return 0

        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Regenerating templates...', total=None)

            files_written, commands_count, agents_count = generate_templates(orchestrator, project_path, platform_type)

            progress.update(task, description='Updating configuration...')

            config['version'] = package_version
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

            progress.update(task, description='Complete!', completed=True)

        console.print()
        if args.force:
            print_success('Templates regenerated successfully')
        else:
            print_success(f'Templates updated: v{current_version} → v{package_version}')
        print_success(f'Regenerated {commands_count} commands and {agents_count} agents')
        console.print()
        print_warning('Restart Claude Code to activate the updated templates')
        console.print()

        return 0

    except json.JSONDecodeError as e:
        print_error(f'Config file is corrupted: {e}')
        print_warning('Delete .respec-ai/config.json and run: respec-ai init')
        return 1

    except ValueError as e:
        print_error(f'Invalid platform in config: {e}')
        return 1

    except Exception as e:
        print_error(f'Regenerate failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Regenerate agent and command templates')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
