import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import ClaudeConfigError, unregister_all_respec_servers
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--project',
        action='store_true',
        help='Also remove .respec-ai configuration from current project',
    )


def run(args: Namespace) -> int:
    try:
        console.print('[yellow]Cleaning up respec-ai installations...[/yellow]')
        console.print()

        removed_mcp = 0
        removed_docker = 0

        try:
            console.print('[dim]Unregistering MCP servers...[/dim]')
            removed_mcp = unregister_all_respec_servers()
            if removed_mcp > 0:
                console.print(f'[green]✓[/green] Removed {removed_mcp} MCP server registration(s)')
            else:
                console.print('[dim]No MCP servers found to remove[/dim]')
        except ClaudeConfigError as e:
            console.print(f'[yellow]⚠[/yellow] MCP cleanup warning: {e}')

        try:
            console.print('[dim]Cleaning up Docker containers and images...[/dim]')
            docker_manager = DockerManager()
            removed_docker = docker_manager.cleanup_old_versions()
            if removed_docker > 0:
                console.print(f'[green]✓[/green] Removed {removed_docker} Docker container(s)/image(s)')
            else:
                console.print('[dim]No Docker containers/images found to remove[/dim]')
        except DockerManagerError as e:
            console.print(f'[yellow]⚠[/yellow] Docker cleanup warning: {e}')

        project_cleaned = False
        if args.project:
            config_path = Path.cwd() / '.respec-ai'
            if config_path.exists():
                console.print('[dim]Removing project configuration...[/dim]')
                shutil.rmtree(config_path)
                console.print('[green]✓[/green] Removed project configuration')
                project_cleaned = True
            else:
                console.print('[dim]No project configuration found[/dim]')

        console.print()
        if removed_mcp > 0 or removed_docker > 0 or project_cleaned:
            console.print('[green]✓[/green] Cleanup complete')
            if removed_mcp > 0:
                console.print('[yellow]⚠[/yellow] Restart Claude Code to apply MCP changes')
        else:
            console.print('[green]✓[/green] Nothing to clean up - system already clean')

        return 0

    except Exception as e:
        console.print(f'[red]✗[/red] Cleanup failed: {e}')
        return 1
