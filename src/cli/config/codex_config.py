import os
import re
from pathlib import Path
from shutil import which
from typing import Any

import tomllib


MCP_SERVER_NAME = 'respec-ai'
MCP_SERVER_ALIASES = ('respec-ai', 'respec_ai', 'respecai')
MCP_COMMAND = 'respec-ai'
MCP_ARGS: list[str] = ['mcp-server']
MCP_STARTUP_TIMEOUT_SEC = 30


class CodexConfigError(Exception):
    pass


def codex_home() -> Path:
    raw = os.environ.get('CODEX_HOME')
    if raw:
        return Path(raw).expanduser()
    return Path.home() / '.codex'


def codex_config_path() -> Path:
    return codex_home() / 'config.toml'


def load_codex_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or codex_config_path()
    if not path.exists():
        return {}

    try:
        return tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as e:
        raise CodexConfigError(f'Codex config is invalid TOML: {e}') from e
    except OSError as e:
        raise CodexConfigError(f'Failed reading Codex config: {e}') from e


def is_mcp_server_registered(config_path: Path | None = None) -> bool:
    try:
        config = load_codex_config(config_path)
        mcp_servers = config.get('mcp_servers', {})
        if not isinstance(mcp_servers, dict):
            return False
        server = mcp_servers.get(MCP_SERVER_NAME)
        if not isinstance(server, dict):
            return False
        command = server.get('command')
        args = server.get('args')
        startup_timeout_sec = server.get('startup_timeout_sec')

        if not isinstance(command, str):
            return False
        if command != MCP_COMMAND and Path(command).name != MCP_COMMAND:
            return False
        if args != MCP_ARGS:
            return False
        return startup_timeout_sec == MCP_STARTUP_TIMEOUT_SEC
    except CodexConfigError:
        return False


def _remove_mcp_server_blocks(content: str, server_name: str) -> tuple[str, int]:
    pattern = re.compile(
        rf'(?m)^\[mcp_servers\.{re.escape(server_name)}(?:\.[^\]]+)?\]\s*\n(?:^(?!\[).*\n?)*',
    )
    updated, count = pattern.subn('', content)
    return updated, count


def _normalize_config_text(content: str) -> str:
    collapsed = re.sub(r'\n{3,}', '\n\n', content).strip()
    return f'{collapsed}\n' if collapsed else ''


def _resolve_mcp_command() -> str:
    resolved = which(MCP_COMMAND)
    return resolved if resolved else MCP_COMMAND


def _toml_escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def _render_mcp_server_block() -> str:
    command = _toml_escape(_resolve_mcp_command())
    return (
        f'[mcp_servers.{MCP_SERVER_NAME}]\n'
        f'command = "{command}"\n'
        f'args = ["{MCP_ARGS[0]}"]\n'
        f'startup_timeout_sec = {MCP_STARTUP_TIMEOUT_SEC}\n'
        'enabled = true\n'
    )


def register_mcp_server(force: bool = False, config_path: Path | None = None) -> bool:
    path = config_path or codex_config_path()

    if is_mcp_server_registered(path) and not force:
        return False

    existing = path.read_text(encoding='utf-8') if path.exists() else ''
    cleaned = existing
    for alias in MCP_SERVER_ALIASES:
        cleaned, _ = _remove_mcp_server_blocks(cleaned, alias)

    block = _render_mcp_server_block()
    normalized = _normalize_config_text(cleaned)
    new_content = f'{normalized}\n{block}' if normalized else block

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding='utf-8')
    except OSError as e:
        raise CodexConfigError(f'Failed writing Codex config: {e}') from e

    return True


def unregister_mcp_server(config_path: Path | None = None) -> bool:
    path = config_path or codex_config_path()
    if not path.exists():
        return False

    existing = path.read_text(encoding='utf-8')
    updated, removed = _remove_mcp_server_blocks(existing, MCP_SERVER_NAME)
    if removed == 0:
        return False

    path.write_text(_normalize_config_text(updated), encoding='utf-8')
    return True


def unregister_all_respec_servers(config_path: Path | None = None) -> int:
    path = config_path or codex_config_path()
    if not path.exists():
        return 0

    existing = path.read_text(encoding='utf-8')
    updated = existing
    removed_total = 0
    for alias in MCP_SERVER_ALIASES:
        updated, removed = _remove_mcp_server_blocks(updated, alias)
        removed_total += removed

    if removed_total > 0:
        path.write_text(_normalize_config_text(updated), encoding='utf-8')
    return removed_total
