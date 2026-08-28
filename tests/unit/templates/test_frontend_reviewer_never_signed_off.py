from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter


def _template(command: RespecAICommand) -> str:
    return TemplateCoordinator().generate_command_template(command, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter())


class TestFrontendReviewerNeverSignsOff:
    def test_code_command_never_adds_frontend_reviewer_to_signed_off_reviewers(self) -> None:
        # B6, B9
        template = _template(RespecAICommand.CODE)

        assert 'NEVER add "frontend-reviewer" to PHASE1_SIGNED_OFF_REVIEWERS' in template
        assert 'respec-ai frontend-preflight --stop' in template

    def test_patch_command_never_adds_frontend_reviewer_to_signed_off_reviewers(self) -> None:
        # B6, B9
        template = _template(RespecAICommand.PATCH)

        assert 'NEVER add "frontend-reviewer" to PHASE1_SIGNED_OFF_REVIEWERS' in template
        assert 'respec-ai frontend-preflight --stop' in template
