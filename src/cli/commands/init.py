import json
import shutil
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.config.claude_config import ClaudeConfigError, add_mcp_permissions, register_mcp_server
from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.cli.config.package_info import PackageInfoError, get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_info, print_warning
from src.cli.ui.formatters import print_setup_complete
from src.cli.ui.stack_prompts import prompt_stack_profile
from src.mcp.tools import register_all_tools
from src.platform.models import ProjectStack
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tooling_defaults import apply_stack_to_tooling, detect_project_stack, detect_project_tooling


def add_arguments(parser: ArgumentParser) -> None:
    """Add command-specific arguments.

    Args:
        parser: Argument parser for this command
    """
    parser.add_argument(
        '-p',
        '--platform',
        required=True,
        choices=['linear', 'github', 'markdown'],
        help='Platform type for workflow integration',
    )
    parser.add_argument(
        '-n',
        '--project-name',
        help='Project name (defaults to directory name)',
    )
    parser.add_argument(
        '--skip-mcp-registration',
        action='store_true',
        help='Skip automatic MCP server registration',
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help='Overwrite existing configuration if present',
    )
    parser.add_argument(
        '-y',
        '--yes',
        action='store_true',
        help='Skip confirmation prompt and accept detected configuration',
    )


def run(args: Namespace) -> int:
    """Initialize respec-ai in current project.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        project_path = Path.cwd().resolve()
        platform = args.platform
        project_name = args.project_name or project_path.name

        respec_ai_dir = project_path / '.respec-ai'
        config_path = respec_ai_dir / 'config.json'

        if config_path.exists():
            if not args.force:
                print_error('respec-ai is already initialized in this project')
                print_warning(f'Config found at: {config_path}')
                print_warning('Use --force to reinitialize completely')
                print_warning('Use respec-ai rebuild to rebuild configuration')
                print_warning('Use respec-ai platform to change platforms')
                print_warning('Use respec-ai regenerate to update templates only')
                return 1
            else:
                print_warning('Force flag detected - reinitializing project')
                if respec_ai_dir.exists():
                    shutil.rmtree(respec_ai_dir)

        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Creating directories...', total=None)

            respec_ai_dir.mkdir(parents=True, exist_ok=True)
            get_commands_dir(project_path).mkdir(parents=True, exist_ok=True)
            get_agents_dir(project_path).mkdir(parents=True, exist_ok=True)

            progress.update(task, description='Detecting project tooling...')
            tooling = detect_project_tooling(project_path)

            progress.update(task, description='Detecting project stack...')
            stack = detect_project_stack(project_path)

            progress.update(task, description='Detection complete!')

        if not args.yes:
            stack = prompt_stack_profile(stack)

        tooling = apply_stack_to_tooling(tooling, stack)

        _display_detected_config(platform, project_name, tooling, stack)

        if not args.yes:
            response = console.input('\n[bold]Proceed with this configuration?[/bold] [Y/n] ')
            if response.strip().lower() in ('n', 'no'):
                print_warning('Initialization cancelled')
                return 1

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Generating templates...', total=None)

            mcp = FastMCP('template-generator')
            register_all_tools(mcp)

            files_written, commands_count, agents_count = generate_templates(
                orchestrator, project_path, platform_type, mcp=mcp, tooling=tooling or None, stack=stack
            )

            progress.update(task, description='Creating configuration...')

            config = {
                'project_name': project_name,
                'platform': platform,
                'created_at': datetime.now().isoformat(),
                'version': get_package_version(),
            }
            if tooling:
                config['tooling'] = {lang: t.model_dump() for lang, t in tooling.items()}
            config['stack'] = stack.model_dump()
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

            mcp_registered = False
            if not args.skip_mcp_registration:
                progress.update(task, description='Verifying Docker installation...')
                try:
                    docker_manager = DockerManager()
                except DockerManagerError as e:
                    print_warning(f'Docker check failed: {e}')
                    print_warning('MCP server requires Docker. Install Docker and try again.')
                    print_warning('Run respec-ai register-mcp to register manually later')
                else:
                    try:
                        progress.update(task, description='Checking Docker image...')
                        if not docker_manager.verify_image_exists():
                            progress.update(task, description='Pulling Docker image...')
                            try:
                                docker_manager.pull_image()
                            except DockerManagerError:
                                print_warning('Failed to pull image from registry')
                                print_info('Run: respec-ai docker build')
                                print_info('Then: respec-ai register-mcp')

                        if docker_manager.verify_image_exists():
                            progress.update(task, description='Starting MCP container...')
                            docker_manager.ensure_running()

                            progress.update(task, description='Registering MCP server...')
                            try:
                                mcp_registered = register_mcp_server()
                                add_mcp_permissions()
                            except (ClaudeConfigError, PackageInfoError) as e:
                                print_warning(f'MCP registration failed: {e}')
                                print_warning('Run respec-ai register-mcp to register manually')

                    except DockerManagerError as e:
                        print_warning(f'Docker setup failed: {e}')
                        print_warning('Run respec-ai docker pull or respec-ai docker build')
                        print_warning('Then: respec-ai register-mcp')

            progress.update(task, description='Complete!', completed=True)

        files_created = len(files_written) + 1

        print_setup_complete(
            project_path=project_path,
            platform=platform,
            files_created=files_created,
            mcp_registered=mcp_registered,
        )

        return 0

    except ValueError as e:
        print_error(f'Invalid platform: {e}')
        return 1

    except Exception as e:
        print_error(f'Initialization failed: {e}')
        return 1


def _display_detected_config(
    platform: str,
    project_name: str,
    tooling: dict,
    stack: ProjectStack,
) -> None:
    table = Table(title='Detected Configuration', show_header=True, header_style='bold cyan')
    table.add_column('Setting', style='bold')
    table.add_column('Value')

    table.add_row('Project Name', project_name)
    table.add_row('Platform', platform)

    if tooling:
        table.add_row('Tooling', ', '.join(tooling.keys()))
    else:
        table.add_row('Tooling', '[dim]none detected[/dim]')

    for field_name, value in stack.model_dump().items():
        label = field_name.replace('_', ' ').title()
        display_value = str(value) if value is not None else '[dim]\u2014[/dim]'
        table.add_row(f'Stack: {label}', display_value)

    console.print()
    console.print(table)


if __name__ == '__main__':
    parser = ArgumentParser(description='Initialize respec-ai in current project')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
