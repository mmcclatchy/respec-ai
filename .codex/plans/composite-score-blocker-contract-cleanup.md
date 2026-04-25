# Composite Score and Blocker Contract Cleanup

## Document Purpose
Track implementation for the final reviewer-loop correctness cleanup: strict composite `100/100` semantics and blank blocker rejection.

## Objective
Ensure composite `100/100` only occurs when every active reviewer awards a perfect local score, and ensure persisted blocker arrays contain only real non-empty blocker strings.

## Locked Decisions
- Keep reviewer weights, local max scores, prompt rubrics, command orchestration, and decision logging unchanged.
- Preserve round-to-nearest composite scoring except cap non-perfect reviewer sets at `99`.
- Use the existing blocker sentinel pathway and extend it to blank/whitespace-only blocker strings.
- Update uncommitted migration `025` directly.

## Execution Checklist (Primary Working Section)
- [x] Update weighted score aggregation so non-perfect reviewer sets cannot return `100`.
- [x] Tighten shared blocker validation for `CriticFeedback`, `ReviewerResult`, and reviewer-result MCP storage.
- [x] Extend migration `025` to remove blank blockers from persisted loop feedback and reviewer results.
- [x] Add model, MCP, and migration test coverage for the new behavior.
- [x] Run requested validation commands and `git diff --check`.

## Verified Current State / Evidence
- `src/mcp/tools/feedback_tools_unified.py` rounds `sum(weighted_contributions.values())`, so a non-perfect score such as `99.85` can display as `100/100`.
- `src/models/feedback.py` rejects known placeholder blocker sentinels but allows blank strings.
- `migrations/025_repair_empty_blocker_placeholders.sql` removes known placeholder sentinels but not blank strings.

## File-by-File Change Plan
- `src/mcp/tools/feedback_tools_unified.py`: preserve current contribution math, but cap rounded non-perfect composite scores at `99`.
- `src/models/feedback.py`: add shared actionable-blocker helpers and apply them to both feedback models.
- `migrations/025_repair_empty_blocker_placeholders.sql`: filter out blank/whitespace-only strings alongside placeholder sentinels.
- `tests/unit/models/test_critic_feedback.py`: cover blank blocker rejection and empty markdown blocker parsing.
- `tests/unit/mcp/test_feedback_tools_unified.py`: cover strict `100` semantics and MCP blank-blocker rejection.
- `tests/unit/utils/test_database_specifics.py`: cover blank blocker migration repair for loop feedback and reviewer results.

## Validation Commands
- `uv run pytest tests/unit/models/test_critic_feedback.py`
- `uv run pytest tests/unit/mcp/test_feedback_tools_unified.py`
- `uv run pytest tests/unit/models/test_enhanced_loop_state.py`
- `uv run pytest tests/unit/utils/test_database_specifics.py`
- `git diff --check`

## Acceptance Criteria
- Composite `100/100` requires every active reviewer to have `score == max_score`.
- A non-perfect active reviewer set that mathematically rounds to `100` returns `99`.
- Blank and whitespace-only blockers are rejected before new model/store persistence.
- Existing blank blockers are repaired to `[]` or removed from mixed arrays by migration `025`.
- Empty `### Blockers` markdown sections still parse to `blockers=[]`.

## Fresh Session Handoff Notes
Implementation complete. Validation passed with the requested model, MCP, loop-state, and database-specific test set plus `git diff --check`.
