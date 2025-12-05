import json
from pathlib import Path

from src.cli.config.package_info import get_package_version


CLAUDE_CONFIG_PATH = Path.home() / '.claude' / 'config.json'
MCP_SERVER_NAME = 'RespecAI'


class ClaudeConfigError(Exception):
    pass


def _create_backup(config_path: Path) -> Path:
    """Create backup of config file before modification.

    Args:
        config_path: Path to config file

    Returns:
        Path to backup file
    """
    if not config_path.exists():
        return config_path.with_suffix('.json.backup')

    backup_path = config_path.with_suffix('.json.backup')
    backup_path.write_text(config_path.read_text(encoding='utf-8'), encoding='utf-8')
    return backup_path


def restore_backup(config_path: Path = CLAUDE_CONFIG_PATH) -> None:
    """Restore config from backup file.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Raises:
        ClaudeConfigError: If backup doesn't exist or restore fails
    """
    backup_path = config_path.with_suffix('.json.backup')

    if not backup_path.exists():
        raise ClaudeConfigError(f'No backup file found at: {backup_path}\nCannot restore configuration.')

    try:
        config_path.write_text(backup_path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception as e:
        raise ClaudeConfigError(f'Failed to restore backup: {e}') from e


def load_claude_config(config_path: Path = CLAUDE_CONFIG_PATH) -> dict:
    """Load Claude Code configuration file.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        Configuration dictionary

    Raises:
        ClaudeConfigError: If Claude Code not installed or config corrupted
    """
    if not config_path.parent.exists():
        raise ClaudeConfigError(
            f'Claude Code does not appear to be installed.\n'
            f'Directory not found: {config_path.parent}\n\n'
            'Install Claude Code first: https://github.com/anthropics/claude-code'
        )

    if not config_path.exists():
        return {'mcpServers': {}}

    try:
        content = config_path.read_text(encoding='utf-8')
        return json.loads(content)
    except json.JSONDecodeError as e:
        backup_path = config_path.with_suffix('.json.backup')
        raise ClaudeConfigError(
            f'Claude config file is corrupted: {config_path}\n'
            f'JSON error: {e}\n\n'
            f'Backup exists at: {backup_path}\n'
            'Restore with: respec-ai register-mcp --restore-backup\n'
            'Or delete the config file and try again.'
        ) from e
    except Exception as e:
        raise ClaudeConfigError(f'Error reading config file: {e}') from e


def save_claude_config(
    config: dict,
    config_path: Path = CLAUDE_CONFIG_PATH,
    create_backup: bool = True,
) -> None:
    """Save Claude Code configuration file.

    Args:
        config: Configuration dictionary
        config_path: Path to config file (defaults to ~/.claude/config.json)
        create_backup: Whether to create backup before saving

    Raises:
        ClaudeConfigError: If save fails or config invalid
    """
    try:
        json.dumps(config)
    except (TypeError, ValueError) as e:
        raise ClaudeConfigError(f'Invalid config structure: {e}') from e

    if create_backup:
        _create_backup(config_path)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    except Exception as e:
        backup_path = config_path.with_suffix('.json.backup')
        raise ClaudeConfigError(
            f'Failed to save config: {e}\n\n'
            f'Config backup preserved at: {backup_path}\n'
            'Run restore_backup() to rollback changes.'
        ) from e


def is_mcp_server_registered(config_path: Path = CLAUDE_CONFIG_PATH) -> bool:
    """Check if RespecAI MCP server is registered.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        True if registered, False otherwise
    """
    try:
        config = load_claude_config(config_path)
        mcp_servers = config.get('mcpServers', {})
        return MCP_SERVER_NAME in mcp_servers
    except ClaudeConfigError:
        return False


def register_mcp_server(
    force: bool = False,
    config_path: Path = CLAUDE_CONFIG_PATH,
) -> bool:
    """Register RespecAI MCP server in Claude Code config.

    Args:
        force: Overwrite existing registration
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        True if registered (new or updated), False if already registered

    Raises:
        ClaudeConfigError: If Claude Code not installed or registration fails
    """
    config = load_claude_config(config_path)

    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    if MCP_SERVER_NAME in config['mcpServers'] and not force:
        return False

    version = get_package_version()
    container_name = f'respec-ai-{version}'

    config['mcpServers'][MCP_SERVER_NAME] = {
        'command': 'docker',
        'args': ['exec', '-i', container_name, 'uv', 'run', 'python', '-m', 'src.mcp.server'],
    }

    save_claude_config(config, config_path)
    return True


def unregister_mcp_server(
    config_path: Path = CLAUDE_CONFIG_PATH,
) -> bool:
    """Remove RespecAI MCP server from Claude Code config.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        True if removed, False if not registered

    Raises:
        ClaudeConfigError: If save fails
    """
    config = load_claude_config(config_path)

    mcp_servers = config.get('mcpServers', {})
    if MCP_SERVER_NAME not in mcp_servers:
        return False

    del mcp_servers[MCP_SERVER_NAME]
    save_claude_config(config, config_path)
    return True


def get_mcp_server_config(config_path: Path = CLAUDE_CONFIG_PATH) -> dict | None:
    """Get RespecAI MCP server configuration.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        MCP server config dict, or None if not registered
    """
    try:
        config = load_claude_config(config_path)
        return config.get('mcpServers', {}).get(MCP_SERVER_NAME)
    except ClaudeConfigError:
        return None
