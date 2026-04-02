import json
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


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

        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'
        tui = 'claude-code'
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding='utf-8'))
                tui = config.get('tui', 'claude-code')
            except (json.JSONDecodeError, OSError):
                pass
        tui_adapter = get_tui_adapter(TuiType(tui))

        removed_mcp = 0
        removed_docker = 0

        try:
            console.print('[dim]Unregistering MCP servers...[/dim]')
            removed_mcp = tui_adapter.unregister_all_mcp_servers(project_path)
            if removed_mcp > 0:
                console.print(f'[green]✓[/green] Removed {removed_mcp} MCP server registration(s)')
            else:
                console.print('[dim]No MCP servers found to remove[/dim]')
        except Exception as e:
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
                console.print(f'[yellow]⚠[/yellow] Restart {tui_adapter.display_name} to apply MCP changes')
        else:
            console.print('[green]✓[/green] Nothing to clean up - system already clean')

        return 0

    except Exception as e:
        console.print(f'[red]✗[/red] Cleanup failed: {e}')
        return 1
