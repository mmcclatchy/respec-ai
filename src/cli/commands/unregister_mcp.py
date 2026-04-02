import json
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import ClaudeConfigError
from src.cli.ui.console import console
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--all',
        action='store_true',
        help='Remove all respec-ai MCP server entries (respec-ai, respec-ai, respec_ai)',
    )


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            console.print('[red]✗[/red] respec-ai is not initialized in this project')
            console.print('[yellow]⚠[/yellow] Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        config = json.loads(config_path.read_text(encoding='utf-8'))
        tui = config.get('tui', 'claude-code')
        tui_adapter = get_tui_adapter(TuiType(tui))

        if args.all:
            removed_count = tui_adapter.unregister_all_mcp_servers(project_path)
            if removed_count == 0:
                console.print('[yellow]No MCP servers found to unregister[/yellow]')
                console.print('[dim]Already clean - no respec-ai MCP servers registered[/dim]')
            else:
                console.print(f'[green]✓[/green] Unregistered {removed_count} MCP server(s)')
                console.print(f'[yellow]⚠[/yellow] Restart {tui_adapter.display_name} to apply changes')
            return 0

        if tui_adapter.unregister_mcp_server(project_path):
            console.print('[green]✓[/green] MCP server "respec-ai" unregistered successfully')
            console.print(f'[yellow]⚠[/yellow] Restart {tui_adapter.display_name} to apply changes')
        else:
            console.print('[yellow]MCP server "respec-ai" was not registered[/yellow]')

        return 0

    except ClaudeConfigError as e:
        console.print(f'[red]✗[/red] Failed to unregister MCP server: {e}')
        return 1
    except Exception as e:
        console.print(f'[red]✗[/red] Unexpected error: {e}')
        return 1
