import json
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn
from src.cli.config.claude_config import ClaudeConfigError, register_mcp_server
from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.cli.config.package_info import PackageInfoError, get_package_version
from src.platform.template_generator import generate_templates
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_info, print_warning
from src.cli.ui.formatters import print_setup_complete
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType


def add_arguments(parser: ArgumentParser) -> None:
    """Add command-specific arguments.

    Args:
        parser: Argument parser for this command
    """
    parser.add_argument(
        '--platform',
        required=True,
        choices=['linear', 'github', 'markdown'],
        help='Platform type for workflow integration',
    )
    parser.add_argument(
        '--project-name',
        help='Project name (defaults to directory name)',
    )
    parser.add_argument(
        '--skip-mcp-registration',
        action='store_true',
        help='Skip automatic MCP server registration',
    )


def run(args: Namespace) -> int:
    """Initialize RespecAI in current project.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        project_path = Path.cwd().resolve()
        platform = args.platform
        project_name = args.project_name or project_path.name

        reRESPEC_AI_dir = project_path / '.respec-ai'
        config_path = reRESPEC_AI_dir / 'config.json'

        if config_path.exists():
            print_error('RespecAI is already initialized in this project')
            print_warning(f'Config found at: {config_path}')
            print_warning('Use respec-ai platform to change platforms')
            print_warning('Use respec-ai upgrade to update templates')
            return 1

        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Creating directories...', total=None)

            reRESPEC_AI_dir.mkdir(parents=True, exist_ok=True)
            get_commands_dir(project_path).mkdir(parents=True, exist_ok=True)
            get_agents_dir(project_path).mkdir(parents=True, exist_ok=True)

            progress.update(task, description='Generating templates...')

            files_written, commands_count, agents_count = generate_templates(orchestrator, project_path, platform_type)

            progress.update(task, description='Creating configuration...')

            config = {
                'project_name': project_name,
                'platform': platform,
                'created_at': datetime.now().isoformat(),
                'version': get_package_version(),
            }
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


if __name__ == '__main__':
    parser = ArgumentParser(description='Initialize RespecAI in current project')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
