# Workflow Input Contract Cleanup Plan

## Summary
Normalize workflow input contracts so free-form guidance is handled deterministically, derived state is not presented as input, naming matches invocation wiring, and ambiguous requests are pushed back to the user instead of guessed.

## Key Changes
- Refactor `respec-code`, `respec-task`, `respec-phase`, and `respec-roadmap` to parse deterministic identifiers first and treat the remaining user input as a single raw guidance payload.
- Add fail-closed ambiguity handling to `respec-code`, `respec-task`, and `respec-phase` so phase-identification vs extra-guidance boundaries are clarified with the user before downstream fan-out.
- Keep derived workflow state out of parse/input sections across commands.
- Clarify shared patch-capable agent contracts so patch workflows use `request_brief`, non-patch workflows use `optional_context`, and the two are not presented as competing primary inputs.
- Fix naming mismatches where templates say `project_name` but helper wiring passes `plan_name`.
- Remove stale `Change Description` wording and other patch-era leftovers that no longer match the current contract.

## Execution Checklist
- [x] Refactor `code`, `task`, `phase`, and `roadmap` command parse contracts to use raw trailing input plus derived workflow state.
- [x] Add fail-closed ambiguity guidance to `code`, `task`, and `phase` around phase reference vs additional guidance.
- [x] Clarify shared patch-capable agent inputs so `optional_context` and `request_brief` have explicit workflow scope and precedence.
- [x] Fix `project_name` vs `plan_name` mismatches and stale patch terminology.
- [x] Update template tests for the new command and agent contracts.
- [x] Run focused and full template tests.
- [x] Leave changes uncommitted for manual review.

## Test Plan
- Update command-template tests to verify:
  - `code`, `task`, and `phase` no longer advertise ambiguous multi-field free-form parse contracts
  - `roadmap` handles trailing guidance as a raw payload plus derived workflow state
  - ambiguity handling requires user interaction instead of silent guessing
- Update template assertions for shared agents so patch-vs-non-patch guidance fields are documented with explicit workflow scope.
- Run the full command-template test file.

## Assumptions
- Command/skill-level user interaction is available for ambiguity resolution.
- Free-form guidance should use the `plan`/`patch` style contract: deterministic identifiers first, then a single trailing raw payload, then clarification before normalization.
- No commit should be created during this pass.
