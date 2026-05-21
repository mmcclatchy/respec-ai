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


def get_tui_adapter(tui_type: TuiType, model_overrides: dict[str, str] | None = None) -> TuiAdapter:
    if tui_type == TuiType.CLAUDE_CODE:
        return ClaudeCodeAdapter()
    if tui_type == TuiType.OPENCODE:
        return OpenCodeAdapter(model_overrides=model_overrides)
    if tui_type == TuiType.CODEX:
        return CodexAdapter(model_overrides=model_overrides)
    raise ValueError(f'Unsupported TUI type: {tui_type}')


__all__ = [
    'AgentSpec',
    'ClaudeCodeAdapter',
    'CodexAdapter',
    'CommandSpec',
    'TuiAdapter',
    'get_tui_adapter',
    'OpenCodeAdapter',
]
