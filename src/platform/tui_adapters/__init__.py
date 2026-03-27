from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter
from src.platform.tui_adapters.claude_code import ClaudeCodeAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter
from src.platform.tui_selector import TuiType


def get_tui_adapter(tui_type: TuiType) -> TuiAdapter:
    if tui_type == TuiType.CLAUDE_CODE:
        return ClaudeCodeAdapter()
    if tui_type == TuiType.OPENCODE:
        return OpenCodeAdapter()
    raise ValueError(f'Unsupported TUI type: {tui_type}')


__all__ = [
    'AgentSpec',
    'ClaudeCodeAdapter',
    'CommandSpec',
    'TuiAdapter',
    'get_tui_adapter',
    'OpenCodeAdapter',
]
