import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn
from src.cli.config.claude_config import ClaudeConfigError, register_mcp_server
from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.cli.config.package_info import PackageInfoError, get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_info, print_success, print_warning
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--skip-mcp-registration',
        action='store_true',
        help='Skip automatic MCP server re-registration',
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
        platform = config.get('platform')
        project_name = config.get('project_name')

        if not platform:
            print_error('Platform not set in config')
            print_warning('Delete .respec-ai/config.json and run: respec-ai init')
            return 1

        package_version = get_package_version()
        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Checking directories...', total=None)

            respec_ai_dir = project_path / '.respec-ai'
            respec_ai_dir.mkdir(parents=True, exist_ok=True)
            get_commands_dir(project_path).mkdir(parents=True, exist_ok=True)
            get_agents_dir(project_path).mkdir(parents=True, exist_ok=True)

            progress.update(task, description='Regenerating templates...')

            files_written, commands_count, agents_count = generate_templates(orchestrator, project_path, platform_type)

            progress.update(task, description='Updating configuration...')

            config['version'] = package_version
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
                        progress.update(task, description='Checking Docker container...')
                        container_status = docker_manager.get_container_status()

                        if not container_status['exists']:
                            print_warning('Docker container does not exist')
                            print_info('Run: respec-ai docker pull')
                            print_info('Then: respec-ai register-mcp')
                        else:
                            if not container_status['running']:
                                progress.update(task, description='Starting Docker container...')
                                docker_manager.ensure_running()

                            progress.update(task, description='Re-registering MCP server...')
                            try:
                                mcp_registered = register_mcp_server(force=True)
                            except (ClaudeConfigError, PackageInfoError) as e:
                                print_warning(f'MCP registration failed: {e}')
                                print_warning('Run respec-ai register-mcp to register manually')

                    except DockerManagerError as e:
                        print_warning(f'Docker setup failed: {e}')
                        print_warning('Run respec-ai docker pull or respec-ai docker build')
                        print_warning('Then: respec-ai register-mcp')

            progress.update(task, description='Complete!', completed=True)

        console.print()
        print_success('Project rebuilt successfully')
        print_success(f'Platform: {platform}')
        print_success(f'Project: {project_name}')
        print_success(f'Version: {package_version}')
        print_success(f'Regenerated {commands_count} commands and {agents_count} agents')
        console.print()

        if mcp_registered:
            print_warning('Restart Claude Code to activate the updated MCP server')
        elif not args.skip_mcp_registration:
            print_warning('MCP server not registered - run: respec-ai register-mcp')

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
        print_error(f'Rebuild failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Rebuild RespecAI project configuration')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
