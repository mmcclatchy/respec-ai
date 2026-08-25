"""Behaviors B1-B7 from docs/phase-refactor/phase-6-task-removal.md.

Task is a prompt-driven workflow, so these pin structure via
tests/support/template_contract.py rather than executing anything (testing.md).
B5 (the stale-env-var trap, finding F14) lives in test_setting_configs.py because it
is a real import-time behavior, not a template contract, and must be observed green
*before* the task_* LoopConfig fields are deleted -- see that file's history.
"""

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter


def _code_command_template() -> str:
    coordinator = TemplateCoordinator()
    return coordinator.generate_command_template(RespecAICommand.CODE, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter())


def _patch_command_template() -> str:
    coordinator = TemplateCoordinator()
    return coordinator.generate_command_template(RespecAICommand.PATCH, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter())


def _phase_command_template() -> str:
    coordinator = TemplateCoordinator()
    return coordinator.generate_command_template(RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter())


def _patch_planner_agent_template() -> str:
    from src.platform.template_helpers import create_patch_planner_agent_tools
    from src.platform.templates.agents import generate_patch_planner_template

    return generate_patch_planner_template(create_patch_planner_agent_tools(ClaudeCodeAdapter()))


def test_coding_workflow_never_resolves_a_task_document() -> None:
    template = _code_command_template()
    assert 'doc_type="task"' not in template
    assert 'doc_type="task_breakdown"' not in template
    assert 'respec-task-planner' not in template
    assert 'respec-task-plan-critic' not in template


def test_coding_workflow_gets_build_order_from_the_implementation_plan() -> None:
    template = _code_command_template()
    assert 'IMPLEMENTATION_PLAN_MARKDOWN = Read(IMPLEMENTATION_PLAN_PATH)' in template
    assert '## Build Order > ### Steps' in template


def test_coding_workflow_refuses_to_start_when_shape_was_never_settled() -> None:
    template = _code_command_template()
    assert 'shape-settled' in template
    assert 'respec-phase' in template


def test_reviewer_selection_still_derives_from_domains_the_phase_touches() -> None:
    template = _code_command_template()
    assert 'STEP_MODES' in template
    assert 'ACTIVE_REVIEWERS' in template


def test_amendment_records_scope_without_manufacturing_a_task_document() -> None:
    command_template = _patch_command_template()
    assert 'doc_type="task"' not in command_template
    assert 'get_review_section' in command_template
    assert 'Design Shape' in command_template or 'Design Decisions' in command_template

    planner_template = _patch_planner_agent_template()
    assert 'store_review_section' in planner_template
    assert 'doc_type="task"' not in planner_template


def test_delivery_intent_resolves_with_one_fewer_precedence_level() -> None:
    template = _code_command_template()
    assert 'PHASE_OVERRIDE' not in template
    assert 'Execution Intent Policy' in template


def test_phase_workflow_chains_to_code_command_with_no_task_generation_step() -> None:
    template = _phase_command_template()
    assert 'respec-task' not in template
    assert 'Automatic Task Generation' not in template
