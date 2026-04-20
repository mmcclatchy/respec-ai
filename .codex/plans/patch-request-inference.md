# Patch Request Inference Exit Plan

## Summary
Simplify `respec-patch` so it accepts one raw request payload after `PLAN_NAME`, infers the concrete change plus any supporting context, and asks clarifying questions when the request is ambiguous.

## Key Changes
- Remove the separate user-facing optional context slot from the patch command surface.
- Treat the second argument as the full raw patch request and have the workflow infer:
  - the explicit change being asked for
  - any supporting context or constraints to share with subagents
- Add clarification behavior for ambiguous requests, including direct questions or option selection when needed.
- Keep downstream patch planner, critic, coder, and consolidator wiring intact, but feed them the derived request/context state rather than a second positional parameter.

## Execution Checklist
- [x] Update the patch command template to accept one raw request payload after `PLAN_NAME`.
- [x] Update patch-oriented agent prompts to infer explicit change vs supporting context from the request.
- [x] Add clarification wording for ambiguous patch requests.
- [x] Update template tests for the new patch interface and inference behavior.
- [x] Run the focused command-template test suite.
- [x] Commit the finalized change set after review.

## Test Plan
- Update patch template tests to assert the patch command advertises a single free-form request payload.
- Add coverage for:
  - a clear request with no extra context
  - a request that includes embedded supporting context
  - an ambiguous request that triggers clarification behavior
- Verify derived patch context still reaches the planner and review chain.

## Assumptions
- `respec-patch` can use direct user interaction to resolve ambiguity.
- The user-provided request text remains the single source of truth.
- Any legacy callers that still include trailing text will be treated as part of the same raw request.
