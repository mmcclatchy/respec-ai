# Grounded Code/Patch Agent Evidence Contract

## Document Purpose

Persist the implementation plan for grounding all `respec-code` and `respec-patch` agents in codebase evidence before decisions, and requiring reviewer issues to cite concrete `file:line` references.

## Objective

Ensure code and patch agents inspect relevant code before acting, and ensure reviewer feedback is grounded with file/line evidence for findings, blockers, and negative assessments.

## Locked Decisions

- Use `relative/path.ext:123` as the required `file:line` format.
- Require `file:line` for every issue, blocker, deduction, negative assessment, and score-impacting reviewer finding.
- Allow command-only failures without `file:line` only when no source location exists; if command output identifies a file, require `file:line`.
- Allow missing/unreadable required files to cite the path and read failure without an invented line number.
- Do not change reviewer scoring weights, max scores, blocker validation, MCP tool signatures, or command orchestration.

## Execution Checklist (Primary Working Section)

- [x] Inspect current templates, tool models, helper wiring, and relevant tests.
- [x] Add previous-feedback tool wiring for frontend, backend API, database, and infrastructure reviewers.
- [x] Add a shared grounded reviewer evidence contract to all code reviewers.
- [x] Add explicit coder no-edit-before-grounding instructions.
- [x] Add patch planner Codebase Evidence output requirements.
- [x] Add task plan critic validation for Codebase Evidence paths/lines.
- [x] Add or update tests for reviewer grounding, feedback wiring, and file-line evidence requirements.
- [x] Run targeted template/model tests and `git diff --check`.

## Verified Current State / Evidence

- `src/platform/templates/agents/coder.py:103` and `src/platform/templates/agents/coder.py:113` require `Read`/`Glob`, but no explicit no-edit-before-grounding gate.
- `src/platform/templates/agents/patch_planner.py:118` through `src/platform/templates/agents/patch_planner.py:124` explores code, but generated tasks do not require `path:line` Codebase Evidence.
- `src/platform/templates/agents/task_plan_critic.py:153` through `src/platform/templates/agents/task_plan_critic.py:168` validates references, but not patch-planner Codebase Evidence.
- `src/platform/templates/agents/automated_quality_checker.py:51` and `src/platform/templates/agents/automated_quality_checker.py:221` require evidence, but need explicit changed-file reads before test-quality findings.
- `src/platform/templates/agents/spec_alignment_reviewer.py:53` and `src/platform/templates/agents/spec_alignment_reviewer.py:181` already require implementation inspection and file-line issue evidence.
- `src/platform/templates/agents/code_quality_reviewer.py:52` and `src/platform/templates/agents/code_quality_reviewer.py:205` already require inspection and file-line findings.
- `src/platform/templates/agents/frontend_reviewer.py:40` through `src/platform/templates/agents/frontend_reviewer.py:53` lacks previous-feedback retrieval.
- `src/platform/templates/agents/backend_api_reviewer.py:40` through `src/platform/templates/agents/backend_api_reviewer.py:52` lacks previous-feedback retrieval.
- `src/platform/templates/agents/database_reviewer.py:40` through `src/platform/templates/agents/database_reviewer.py:53` lacks previous-feedback retrieval.
- `src/platform/templates/agents/infrastructure_reviewer.py:40` through `src/platform/templates/agents/infrastructure_reviewer.py:53` lacks previous-feedback retrieval, and `src/platform/templates/agents/infrastructure_reviewer.py:181` uses generic file references.
- `src/platform/templates/agents/coding_standards_reviewer.py:49` through `src/platform/templates/agents/coding_standards_reviewer.py:50` uses `git diff`, but should explicitly require reading each changed file before reporting violations.
- `src/platform/models/code.py:248` through `src/platform/models/code.py:316` omits `GET_FEEDBACK` and `retrieve_feedback` for frontend, backend API, database, and infrastructure reviewers.
- `src/platform/template_helpers.py:1168` through `src/platform/template_helpers.py:1293` omits `retrieve_feedback` wiring for those four reviewers.

## File-by-File Change Plan

- `src/platform/models/code.py`: add `GET_FEEDBACK` and `retrieve_feedback` to frontend, backend API, database, and infrastructure reviewer tool models.
- `src/platform/template_helpers.py`: wire `retrieve_feedback=RespecAITool.GET_FEEDBACK.value` for those four reviewer template helpers.
- `src/platform/templates/agents/*.py`: add consistent grounding/evidence language to all code reviewers, and targeted grounding instructions to coder, patch planner, and task plan critic.
- `tests/unit/templates/test_review_agent_templates.py`: add tests for shared reviewer evidence contract, domain reviewer previous-feedback retrieval, infrastructure `file:line`, and patch/coder/critic grounding text.
- Additional existing tests may be updated only if current test structure locates these assertions elsewhere.

## Validation Commands

- `uv run pytest tests/unit/templates/test_review_agent_templates.py`
- Existing focused template/model tests for `src/platform/models/code.py` and `src/platform/template_helpers.py`, if separate.
- `git diff --check`

## Acceptance Criteria

- Every code reviewer instructs agents to read relevant files before findings and cite `file:line` for issues/blockers.
- Frontend, backend API, database, and infrastructure reviewers retrieve previous feedback.
- Coder template contains a clear no-edit-before-grounding gate.
- Patch planner emits Codebase Evidence with `path:line` facts.
- Task plan critic validates Codebase Evidence paths/lines.
- Targeted tests and diff check pass.

## Fresh Session Handoff Notes

Implementation completed and validated on 2026-04-25.

Validation evidence:
- `uv run pytest tests/unit/templates/test_review_agent_templates.py tests/unit/templates/test_agent_templates.py` passed: 91 tests.
- `uv run pytest tests/unit/platform_tests/test_tool_enums_and_validation.py` passed: 25 tests.
- `git diff --check` passed.

Preserve scoring/blocker changes from commit `08c8ae6`.
