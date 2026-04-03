# Repository Guardrails

## Codex Plan Persistence (Mandatory)

For any non-trivial implementation effort (multi-step, cross-file, or iterative):

1. Create or update a Codex session plan in `./.codex/plans/<plan-name>.md`.
2. Update `./.codex/plans/ACTIVE.md` to point to the active plan file.
3. Treat the on-disk plan as the implementation source of truth if chat context compacts.
4. Keep an execution checklist in the plan and update it as work progresses.
5. Before completing implementation, verify the plan acceptance criteria are satisfied.

## Scope Clarification

- These are Codex session plans, not respec-ai product plan artifacts.
- Do not store Codex session plans under `.respec-ai/plans/`.

## Allowed Exception

Skip plan persistence only for truly trivial single-file/single-step changes when the user explicitly asks to skip it.
