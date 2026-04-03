import json
import shutil
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Table

from src.cli.config.claude_config import ClaudeConfigError
from src.cli.config.codex_config import CodexConfigError
from src.cli.config.package_info import PackageInfoError, get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_info, print_warning
from src.cli.ui.formatters import print_setup_complete
from src.cli.ui.stack_prompts import prompt_stack_profile
from src.mcp.tools import register_all_tools
from src.platform.config_writer import write_config_files
from src.platform.models import ProjectStack
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tooling_defaults import apply_stack_to_tooling, detect_project_stack, detect_project_tooling
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_selector import TuiType


def add_arguments(parser: ArgumentParser) -> None:
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
    parser.add_argument(
        '--tui',
        choices=[t.value for t in TuiType],
        default='claude-code',
        help='Terminal UI to generate files for (default: claude-code)',
    )
    parser.add_argument(
        '--aa-key',
        help='Artificial Analysis API key for OpenCode model benchmarks',
    )
    parser.add_argument(
        '--exa-key',
        help='Exa API key for OpenCode rate limit lookup',
    )


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        platform = args.platform
        project_name = args.project_name or project_path.name

        respec_ai_dir = project_path / '.respec-ai'
        config_path = respec_ai_dir / 'config.json'

        existing_config_files = False

        if config_path.exists():
            if args.force:
                print_warning('Force flag detected - reinitializing project')
                shutil.rmtree(respec_ai_dir)
            else:
                result = _handle_existing_config(args, project_path)
                if result is None:
                    return 1
                existing_config_files = result

        tui = getattr(args, 'tui', 'claude-code')
        platform_type = PlatformType(platform)
        tui_adapter = get_tui_adapter(TuiType(tui))
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Creating directories...', total=None)

            respec_ai_dir.mkdir(parents=True, exist_ok=True)

            if existing_config_files:
                progress.update(task, description='Using existing stack configuration...')
                stack = ProjectStack()
                tooling: dict = {}
            else:
                progress.update(task, description='Detecting project tooling...')
                tooling = detect_project_tooling(project_path)

                progress.update(task, description='Detecting project stack...')
                stack = detect_project_stack(project_path)

                progress.update(task, description='Detection complete!')

        if not existing_config_files and not args.yes:
            stack = prompt_stack_profile(stack)

        if not existing_config_files:
            tooling = apply_stack_to_tooling(tooling, stack)
            _display_detected_config(platform, project_name, tooling, stack)

            if not args.yes:
                response = console.input('\n[bold]Proceed with this configuration?[/bold] [Y/n] ')
                if response.strip().lower() in ('n', 'no'):
                    print_warning('Initialization cancelled')
                    return 1

        result = tui_adapter.post_init_setup(args)
        if result != 0:
            return result

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Generating templates...', total=None)

            mcp = FastMCP('template-generator')
            register_all_tools(mcp)

            files_written, commands_count, agents_count = generate_templates(
                orchestrator, project_path, platform_type, mcp=mcp, tui_adapter=tui_adapter
            )

            progress.update(task, description='Creating configuration...')

            config_dir = project_path / '.respec-ai' / 'config'
            if not config_dir.exists():
                config_files = write_config_files(project_path, stack, tooling or {})
                files_written.extend(config_files)
            else:
                print_info('Config files exist at .respec-ai/config/ — not modified')

            config = {
                'project_name': project_name,
                'platform': platform,
                'tui': tui,
                'created_at': datetime.now().isoformat(),
                'version': get_package_version(),
            }
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

            mcp_registered = _setup_mcp_server(args, progress, task, tui_adapter, project_path)

            progress.update(task, description='Complete!', completed=True)

        print_setup_complete(
            project_path=project_path,
            platform=platform,
            files_created=len(files_written) + 1,
            mcp_registered=mcp_registered,
            tui_display_name=tui_adapter.display_name,
            command_examples=[
                tui_adapter.render_command_invocation(
                    'respec-plan', '[plan-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-roadmap', '[plan-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-phase', '[plan-name] [phase-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-code', '[plan-name] [phase-name]', '', requires_user_interaction=False
                ),
            ],
        )

        return 0

    except ValueError as e:
        print_error(f'Invalid platform: {e}')
        return 1

    except Exception as e:
        print_error(f'Initialization failed: {e}')
        return 1


def _handle_existing_config(args: Namespace, project_path: Path) -> bool | None:
    config_dir = project_path / '.respec-ai' / 'config'

    if not config_dir.exists():
        print_info('Upgrading from previous config format — detecting stack...')
        return False

    print_info('Stack configuration already exists')

    if args.yes:
        print_info('Using existing stack configuration (--yes flag)')
        return True

    console.print()
    console.print('[bold cyan]Choose an option:[/bold cyan]')
    console.print('  [bold]1)[/bold] Keep existing stack configuration (regenerate templates only)')
    console.print('  [bold]2)[/bold] Reconfigure stack (full setup)')
    console.print()

    choice = console.input('[bold]Enter choice (1 or 2):[/bold] ').strip()

    if choice == '1':
        print_info('Using existing stack configuration')
        return True
    if choice == '2':
        shutil.rmtree(config_dir)
        print_info('Reconfiguring stack...')
        return False

    print_error('Invalid choice. Exiting.')
    return None


def _setup_mcp_server(
    args: Namespace,
    progress: Progress,
    task: TaskID,
    tui_adapter: TuiAdapter,
    project_path: Path,
) -> bool:
    if args.skip_mcp_registration:
        return False

    progress.update(task, description='Verifying Docker installation...')
    try:
        docker_manager = DockerManager()
    except DockerManagerError as e:
        print_warning(f'Docker check failed: {e}')
        print_warning('MCP server requires Docker. Install Docker and try again.')
        print_warning('Run respec-ai register-mcp to register manually later')
        return False

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

        if not docker_manager.verify_image_exists():
            return False

        progress.update(task, description='Starting MCP container...')
        docker_manager.ensure_running()

        progress.update(task, description='Registering MCP server...')
        try:
            mcp_registered = tui_adapter.register_mcp_server(project_path)
            tui_adapter.add_mcp_permissions(project_path)
            return mcp_registered
        except (ClaudeConfigError, CodexConfigError, PackageInfoError) as e:
            print_warning(f'MCP registration failed: {e}')
            print_warning('Run respec-ai register-mcp to register manually')
            return False

    except DockerManagerError as e:
        print_warning(f'Docker setup failed: {e}')
        print_warning('Run respec-ai docker pull or respec-ai docker build')
        print_warning('Then: respec-ai register-mcp')
        return False


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
