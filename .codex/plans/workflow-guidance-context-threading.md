# Workflow Guidance Context Threading

## Document Purpose
Track the standardization of optional guidance/context propagation across `respec-task`, `respec-code`, and `respec-patch`.

## Objective
Ensure each workflow accepts optional user guidance, preserves it through retries/resume branches, and forwards it to subagents and reviewers when applicable.

## Locked Decisions
- Keep `plan`, `roadmap`, and `phase` workflows as the existing reference pattern.
- Add optional guidance to `task`, `code`, and `patch` without breaking their existing primary arguments.
- Thread guidance into subagent invocations rather than handling it only at the top-level command.
- Treat pre-commit side effects at workflow completion as normal and commit the full tree.

## Execution Checklist (Primary Working Section)
- [x] Add optional context parsing to `respec-task`, `respec-code`, and `respec-patch`.
- [x] Update template helper command handoffs so downstream invocations advertise the optional context slot.
- [x] Thread optional context into task, code, patch, and review agent templates.
- [x] Preserve patch change-description parsing so multi-word descriptions are still supported.
- [x] Add focused tests for the new command-template behavior.
- [x] Run the targeted template test suite.
- [ ] Commit the finalized change set after review.

## Acceptance Criteria
- `respec-task`, `respec-code`, and `respec-patch` all document an optional guidance/context argument.
- That guidance is forwarded to the relevant downstream agents/reviewers.
- Patch command parsing still supports multi-word change descriptions.
- Targeted template tests pass.
