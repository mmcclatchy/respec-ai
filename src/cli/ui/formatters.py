from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from src.cli.ui.console import console


def format_project_config_table(
    project_path: Path,
    platform: str,
    version: str,
    package_version: str,
    mcp_registered: bool,
) -> Table:
    """Format project configuration as a Rich table.

    Args:
        project_path: Path to project directory
        platform: Platform name (linear, github, markdown)
        version: Project config version
        package_version: Installed package version
        mcp_registered: Whether MCP server is registered

    Returns:
        Rich Table object
    """
    table = Table(title='Project Configuration', show_header=False, box=None)
    table.add_column('Setting', style='cyan', no_wrap=True)
    table.add_column('Value', style='white')

    table.add_row('Project Path', str(project_path))
    table.add_row('Platform', platform)
    table.add_row('Config Version', version)
    table.add_row('Package Version', package_version)

    mcp_status = '[green]✓ Registered[/green]' if mcp_registered else '[red]✗ Not Registered[/red]'
    table.add_row('MCP Server', f'RespecAI ({mcp_status})')

    return table


def format_validation_table(
    checks: dict[str, tuple[bool, str]],
) -> Table:
    """Format validation results as a Rich table.

    Args:
        checks: Dictionary mapping check name to (passed, message) tuple

    Returns:
        Rich Table object
    """
    table = Table(title='Validation Results', show_header=False, box=None)
    table.add_column('Check', style='cyan', no_wrap=True)
    table.add_column('Status', style='white')

    for check_name, (passed, message) in checks.items():
        if passed:
            status = f'[green]✓[/green] {message}'
        else:
            status = f'[red]✗[/red] {message}'

        table.add_row(check_name, status)

    return table


def format_file_counts_table(
    commands_count: int,
    agents_count: int,
    expected_commands: int = 5,
    expected_agents: int = 12,
) -> Table:
    """Format file counts as a Rich table.

    Args:
        commands_count: Number of command files found
        agents_count: Number of agent files found
        expected_commands: Expected number of commands
        expected_agents: Expected number of agents

    Returns:
        Rich Table object
    """
    table = Table(title='Generated Files', show_header=False, box=None)
    table.add_column('Category', style='cyan', no_wrap=True)
    table.add_column('Count', style='white')

    commands_status = (
        f'[green]{commands_count}[/green]'
        if commands_count == expected_commands
        else f'[yellow]{commands_count}[/yellow] (expected {expected_commands})'
    )
    table.add_row('Commands', commands_status)

    agents_status = (
        f'[green]{agents_count}[/green]'
        if agents_count == expected_agents
        else f'[yellow]{agents_count}[/yellow] (expected {expected_agents})'
    )
    table.add_row('Agents', agents_status)

    return table


def print_setup_complete(
    project_path: Path,
    platform: str,
    files_created: int,
    mcp_registered: bool,
) -> None:
    """Print setup completion message with Rich formatting.

    Args:
        project_path: Path to project directory
        platform: Platform name
        files_created: Number of files created
        mcp_registered: Whether MCP was registered
    """
    console.print()
    console.print('[bold green]✅ RespecAI setup complete![/bold green]')
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column('Setting', style='cyan', no_wrap=True)
    table.add_column('Value', style='white')

    table.add_row('Platform', platform)
    table.add_row('Files Created', str(files_created))
    table.add_row('Location', str(project_path))

    if mcp_registered:
        table.add_row('MCP Server', '[green]✓ Registered as RespecAI[/green]')
    else:
        table.add_row('MCP Server', '[yellow]⚠ Skipped[/yellow]')

    console.print(table)
    console.print()

    if not mcp_registered:
        console.print(
            '[yellow]⚠[/yellow]  MCP registration skipped. Run [cyan]respec-ai register-mcp[/cyan] to register manually.'
        )
        console.print()

    console.print(
        '[bold]Available Commands:[/bold] (restart Claude Code to activate)',
    )
    console.print('  • [cyan]/respec-plan[/cyan] - Create strategic plans')
    console.print('  • [cyan]/respec-roadmap[/cyan] - Create phased roadmaps')
    console.print('  • [cyan]/respec-spec[/cyan] - Transform plans into specs')
    console.print('  • [cyan]/respec-build[/cyan] - Execute implementation')
    console.print()
    console.print(
        '[bold yellow]🚀 Ready to begin![/bold yellow] Restart Claude Code to use the RespecAI commands.',
    )
    console.print()


def print_validation_report(
    project_path: Path,
    checks: dict[str, tuple[bool, str]],
    all_passed: bool,
) -> None:
    """Print validation report with Rich formatting.

    Args:
        project_path: Path to project directory
        checks: Dictionary of validation checks
        all_passed: Whether all checks passed
    """
    console.print()

    if all_passed:
        panel = Panel(
            '[bold green]All validation checks passed![/bold green]',
            border_style='green',
        )
        console.print(panel)
    else:
        panel = Panel(
            '[bold yellow]Some validation checks failed[/bold yellow]',
            border_style='yellow',
        )
        console.print(panel)

    console.print()
    console.print(f'[bold]Project:[/bold] {project_path}')
    console.print()

    table = format_validation_table(checks)
    console.print(table)
    console.print()

    if not all_passed:
        console.print('[yellow]⚠[/yellow]  Run [cyan]respec-ai init[/cyan] to fix missing files')
        console.print()
