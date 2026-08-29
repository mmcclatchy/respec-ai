from src.platform.models import FrontendCoderAgentTools
from src.platform.templates.agents.coder_contracts import (
    render_coder_checklist_usage_contract,
    render_coder_completion_checklist_contract,
    render_coder_error_handling_contract,
    render_coder_feedback_integration_contract,
    render_coder_filesystem_boundary_contract,
    render_coder_handoff_contract,
    render_coder_invocation_contract,
    render_coder_iteration_strategy_contract,
    render_coder_loop_ids_contract,
    render_coder_ownership_boundary_contract,
    render_coder_project_configuration_contract,
    render_coder_research_integration_contract,
    render_coder_standards_only_mode_contract,
    render_coder_static_analysis_contract,
    render_coder_task_phase_adherence_contract,
    render_coder_tdd_cycle_contract,
    render_coder_todo_list_structure_contract,
    render_coder_todolist_gate_contract,
    render_coder_tool_invocation_contract,
    render_coder_workflow_heading_contract,
    render_coder_workflow_steps_contract,
)
from src.utils.materializers import sentinel_table


def generate_frontend_coder_template(tools: FrontendCoderAgentTools) -> str:
    # Data-driven from the materializer registry (F9), same as the backend coder --
    # a TypeScript skeleton stubs with its own sentinel, never Python's.
    sentinel_examples = ', '.join(
        f'`{sentinel}` for {language}' for language, sentinel in sorted(sentinel_table().items())
    )
    invocation_contract = render_coder_invocation_contract()
    standards_only_mode_contract = render_coder_standards_only_mode_contract()
    tool_invocation_contract = render_coder_tool_invocation_contract()
    filesystem_boundary_contract = render_coder_filesystem_boundary_contract()
    ownership_boundary_contract = render_coder_ownership_boundary_contract('frontend')
    todolist_gate_contract = render_coder_todolist_gate_contract()
    workflow_heading_contract = render_coder_workflow_heading_contract()
    workflow_steps_contract = render_coder_workflow_steps_contract(
        tools.retrieve_implementation_plan, tools.retrieve_phase, tools.retrieve_feedback
    )
    project_configuration_contract = render_coder_project_configuration_contract()
    research_integration_contract = render_coder_research_integration_contract(
        str(tools.research_directory_pattern), str(tools.research_example_path)
    )
    checklist_usage_contract = render_coder_checklist_usage_contract()
    loop_ids_contract = render_coder_loop_ids_contract(tools.retrieve_feedback)
    tdd_cycle_contract = render_coder_tdd_cycle_contract()
    todo_list_structure_contract = render_coder_todo_list_structure_contract()
    task_phase_adherence_contract = render_coder_task_phase_adherence_contract(sentinel_examples)
    feedback_integration_contract = render_coder_feedback_integration_contract(tools.retrieve_feedback)
    iteration_strategy_contract = render_coder_iteration_strategy_contract()
    handoff_contract = render_coder_handoff_contract()
    static_analysis_contract = render_coder_static_analysis_contract()
    error_handling_contract = render_coder_error_handling_contract()
    completion_checklist_contract = render_coder_completion_checklist_contract()

    return f"""---
name: respec-frontend-coder
description: Implement UI code using strict TDD methodology, scored against the UX Contract
model: {tools.tui_adapter.coding_model}
color: green
tools: {tools.tools_yaml}
---

# respec-frontend-coder Agent

You are the frontend implementation specialist, focused on producing production-ready
component, route, and page-level UI code through strict Test-Driven Development (TDD)
methodology, conforming to the Phase's UX Contract.

{invocation_contract}

{standards_only_mode_contract}

{tool_invocation_contract}

{filesystem_boundary_contract}

{ownership_boundary_contract}

{workflow_heading_contract}

{todolist_gate_contract}

{workflow_steps_contract}

## FRONTEND WORK UNITS

- Checklist items in your domain are component, route, or page-level, as classified by
  the project's language extension map (templates/, static/, components/, and
  frontend-flavored file extensions).
- A component test asserts rendered output for each state named in the Phase's UX
  Contract `##### States` — loading, empty, error, populated, and any others listed —
  not implementation internals.
- Treat accessibility as a build-time requirement, not a review-time surprise: implement
  the UX Contract's `##### Accessibility Requirements` (keyboard reachability, ARIA
  roles, focus management) in the same TDD cycle as functional behavior, not as a
  follow-up pass.
- Honor `##### Breakpoints` from the UX Contract when implementing responsive behavior.
- Wire calls into backend endpoints per Phase `### Collaboration And Wiring` and the
  contract's declared request/response shapes; do not invent an endpoint shape the
  design layer did not declare.
- If the UX Contract names a `##### Design Source`, match its tokens, layout, and
  component structure rather than improvising visual design.

{project_configuration_contract}

{research_integration_contract}

{checklist_usage_contract}

{loop_ids_contract}

{tdd_cycle_contract}

{todo_list_structure_contract}

{task_phase_adherence_contract}

{feedback_integration_contract}

{iteration_strategy_contract}

{handoff_contract}

{static_analysis_contract}

{error_handling_contract}

{completion_checklist_contract}
"""
