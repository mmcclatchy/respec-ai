from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter
from src.platform.tui_adapters.claude_code import ClaudeCodeAdapter
from src.platform.tui_adapters.codex import CodexAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter
from src.platform.tui_selector import TuiType


_ADAPTER_MAP: dict[TuiType, type[TuiAdapter]] = {
    TuiType.CLAUDE_CODE: ClaudeCodeAdapter,
    TuiType.OPENCODE: OpenCodeAdapter,
    TuiType.CODEX: CodexAdapter,
}


def get_tui_adapter(tui_type: TuiType) -> TuiAdapter:
    adapter_cls = _ADAPTER_MAP.get(tui_type)
    if adapter_cls is None:
        raise ValueError(f'Unsupported TUI type: {tui_type}')
    return adapter_cls()


__all__ = [
    'AgentSpec',
    'ClaudeCodeAdapter',
    'CodexAdapter',
    'CommandSpec',
    'TuiAdapter',
    'get_tui_adapter',
    'OpenCodeAdapter',
]
