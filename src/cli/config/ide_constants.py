"""IDE-specific constants and path helpers.

Claude Code specific implementation for v0.2.0.
Future: Replace with IDE adapter system for multi-IDE support.
"""

from pathlib import Path


IDE_NAME = 'claude-code'
IDE_CONFIG_PATH = Path.home() / '.claude' / 'config.json'
IDE_COMMANDS_DIR = '.claude/commands'
IDE_AGENTS_DIR = '.claude/agents'
MCP_SERVER_NAME = 'RespecAI'


def get_commands_dir(project_path: Path) -> Path:
    """Get IDE commands directory for project.

    Args:
        project_path: Project root directory

    Returns:
        Path to commands directory
    """
    return project_path / IDE_COMMANDS_DIR


def get_agents_dir(project_path: Path) -> Path:
    """Get IDE agents directory for project.

    Args:
        project_path: Project root directory

    Returns:
        Path to agents directory
    """
    return project_path / IDE_AGENTS_DIR


def get_ide_config_path() -> Path:
    """Get IDE configuration file path.

    Returns:
        Path to IDE config file (e.g., ~/.claude/config.json)
    """
    return IDE_CONFIG_PATH


def get_mcp_server_name() -> str:
    """Get MCP server name for IDE registration.

    Returns:
        MCP server name (e.g., 'RespecAI')
    """
    return MCP_SERVER_NAME
