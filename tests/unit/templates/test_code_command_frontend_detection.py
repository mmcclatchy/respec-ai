from src.platform.models import PlatformType
from src.platform.template_helpers import create_code_command_tools
from src.platform.templates.commands.code_command import generate_code_command_template
from src.platform.tui_adapters import ClaudeCodeAdapter


def _render() -> str:
    tools = create_code_command_tools(
        'mcp__linear-server__get_issue',
        'mcp__linear-server__create_comment',
        PlatformType.LINEAR,
        tui_adapter=ClaudeCodeAdapter(),
    )
    return generate_code_command_template(tools)


def test_frontend_step_mode_detection_recognizes_extensions_beyond_the_original_hardcoded_list() -> None:
    # B11 / F14: STEP_MODES frontend detection is derived from the shared extension map
    # rather than a second hardcoded list, so an .astro project activates frontend mode.
    rendered = _render()
    assert '.astro' in rendered
    assert '.tsx' in rendered
    assert '.vue' in rendered
