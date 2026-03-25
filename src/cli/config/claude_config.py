import json
import subprocess
from pathlib import Path


CLAUDE_CONFIG_PATH = Path.home() / '.claude' / 'config.json'
CLAUDE_SETTINGS_PATH = Path.home() / '.claude' / 'settings.json'
CLAUDE_SETTINGS_LOCAL_PATH = Path.home() / '.claude' / 'settings.local.json'
MCP_SERVER_NAME = 'respec-ai'
MCP_COMMAND: str = 'respec-ai'
MCP_ARGS: list[str] = ['mcp-server']
EXPECTED_MCP_CONFIG = {
    'command': MCP_COMMAND,
    'args': MCP_ARGS,
}


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
    try:
        config = load_claude_config(config_path)
        server_config = config.get('mcpServers', {}).get(MCP_SERVER_NAME)
        if server_config is None:
            return False
        if server_config.get('env', {}).get('STATE_MANAGER') == 'memory':
            return False
        if 'cwd' in server_config:
            return False
        if server_config.get('command') != EXPECTED_MCP_CONFIG['command']:
            return False
        if server_config.get('args') != EXPECTED_MCP_CONFIG['args']:
            return False
        return True
    except ClaudeConfigError:
        return False


def _claude_mcp_remove(name: str) -> None:
    subprocess.run(['claude', 'mcp', 'remove', name], capture_output=True)


def _claude_mcp_add_user(name: str, command: str, args: list[str]) -> bool:
    result = subprocess.run(
        ['claude', 'mcp', 'add', '-s', 'user', '-t', 'stdio', name, '--', command, *args],
        capture_output=True,
    )
    return result.returncode == 0


def register_mcp_server(
    force: bool = False,
    config_path: Path = CLAUDE_CONFIG_PATH,
) -> bool:
    if is_mcp_server_registered(config_path) and not force:
        return False

    _claude_mcp_remove(MCP_SERVER_NAME)
    _claude_mcp_add_user(MCP_SERVER_NAME, MCP_COMMAND, MCP_ARGS)

    config = load_claude_config(config_path)
    config.setdefault('mcpServers', {})[MCP_SERVER_NAME] = EXPECTED_MCP_CONFIG.copy()
    save_claude_config(config, config_path)
    return True


def unregister_mcp_server(
    config_path: Path = CLAUDE_CONFIG_PATH,
) -> bool:
    config = load_claude_config(config_path)
    mcp_servers = config.get('mcpServers', {})

    if MCP_SERVER_NAME not in mcp_servers:
        return False

    _claude_mcp_remove(MCP_SERVER_NAME)
    del mcp_servers[MCP_SERVER_NAME]
    save_claude_config(config, config_path)
    return True


def unregister_all_respec_servers(config_path: Path = CLAUDE_CONFIG_PATH) -> int:
    """Remove all respec-ai MCP server entries (handles old and new names).

    Removes all variations of respec-ai MCP server names that may exist from
    different versions, including 'respec-ai', 'respec-ai', and 'respec_ai'.

    Args:
        config_path: Path to config file (defaults to ~/.claude/config.json)

    Returns:
        Number of MCP server entries removed

    Raises:
        ClaudeConfigError: If Claude Code is not installed or save fails
    """
    config = load_claude_config(config_path)
    mcp_servers = config.get('mcpServers', {})

    removed_count = 0
    for name in ['respec-ai', 'respec-ai', 'respec_ai']:
        if name in mcp_servers:
            del mcp_servers[name]
            removed_count += 1

    if removed_count > 0:
        save_claude_config(config, config_path)

    return removed_count


def get_mcp_server_config(config_path: Path = CLAUDE_CONFIG_PATH) -> dict | None:
    """Get respec-ai MCP server configuration.

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


def add_mcp_permissions() -> bool:
    """Add respec-ai MCP permissions to Claude settings.

    Checks both settings.json and settings.local.json (prefers local).
    Adds wildcard permission for all respec-ai MCP tools.

    Returns:
        True if permissions were added, False if already present or if settings don't exist

    Raises:
        ClaudeConfigError: If settings file is corrupted or update fails
    """
    settings_path = CLAUDE_SETTINGS_LOCAL_PATH if CLAUDE_SETTINGS_LOCAL_PATH.exists() else CLAUDE_SETTINGS_PATH

    if not settings_path.exists():
        return False

    try:
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise ClaudeConfigError(f'Settings file is corrupted: {e}') from e

    if 'permissions' not in settings:
        settings['permissions'] = {}
    if 'allow' not in settings['permissions']:
        settings['permissions']['allow'] = []

    permission_pattern = f'mcp__{MCP_SERVER_NAME.lower()}__*'

    if permission_pattern in settings['permissions']['allow']:
        return False

    settings['permissions']['allow'].append(permission_pattern)

    try:
        settings_path.write_text(json.dumps(settings, indent=4), encoding='utf-8')
        return True
    except Exception as e:
        raise ClaudeConfigError(f'Failed to update settings: {e}') from e
