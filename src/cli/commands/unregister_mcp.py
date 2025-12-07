from argparse import ArgumentParser, Namespace

from src.cli.config.claude_config import (
    ClaudeConfigError,
    unregister_all_respec_servers,
    unregister_mcp_server,
    MCP_SERVER_NAME,
)
from src.cli.ui.console import console


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--all',
        action='store_true',
        help='Remove all respec-ai MCP server entries (respec-ai, RespecAI, respec_ai)',
    )


def run(args: Namespace) -> int:
    try:
        if args.all:
            removed_count = unregister_all_respec_servers()

            if removed_count == 0:
                console.print('[yellow]No MCP servers found to unregister[/yellow]')
                console.print('[dim]Already clean - no respec-ai MCP servers registered[/dim]')
            else:
                console.print(f'[green]✓[/green] Unregistered {removed_count} MCP server(s)')
                console.print('[yellow]⚠[/yellow] Restart Claude Code to apply changes')
            return 0
        else:
            if unregister_mcp_server():
                console.print(f'[green]✓[/green] MCP server "{MCP_SERVER_NAME}" unregistered successfully')
                console.print('[yellow]⚠[/yellow] Restart Claude Code to apply changes')
                return 0
            else:
                console.print(f'[yellow]MCP server "{MCP_SERVER_NAME}" was not registered[/yellow]')
                return 0

    except ClaudeConfigError as e:
        console.print(f'[red]✗[/red] Failed to unregister MCP server: {e}')
        return 1
    except Exception as e:
        console.print(f'[red]✗[/red] Unexpected error: {e}')
        return 1
