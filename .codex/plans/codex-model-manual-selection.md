# Codex Model Manual Selection

## Document Purpose
Track implementation work to make `respec-ai models codex` use live Codex model discovery with optional Codex CLI update prompting and manual tier selection only.

## Objective
Remove hardcoded Codex model recommendation behavior, prompt users before optionally updating the Codex CLI, and keep model options grounded in `codex app-server` discovery.

## Locked Decisions
- Available Codex models come from `codex app-server --listen stdio://` `model/list`.
- The command prompts to update Codex via `npm install -g @openai/codex` before discovery unless an update flag decides it.
- `--update-codex` approves the update prompt automatically.
- `--no-update-codex` denies the update prompt automatically.
- Codex recommendations, hardcoded priors, inferred scores, and `--yes` are removed.
- Direct non-interactive setup requires all four tier model flags.
- Artificial Analysis data is optional context only and does not drive selection.

## Execution Checklist (Primary Working Section)
- [x] Refactor Codex model command arguments and update prompt flow.
- [x] Remove recommendation and hardcoded-prior code paths.
- [x] Replace score-sorted selection with discovery-order manual selection.
- [x] Update parser and command tests.
- [x] Run targeted pytest, ruff, and ty checks.

## Verified Current State / Evidence
- `codex_model.py` already has working dynamic discovery through Codex app-server `model/list`.
- Live discovery was manually tested with Codex CLI 0.122.0 and returned normalized models.
- `codex_model.py` no longer has `_KNOWN_PRIORS`, inferred scoring, recommendations, or `--yes`.
- Targeted pytest, ruff, and ty checks pass.

## File-by-File Change Plan
- `src/cli/commands/codex_model.py`: add update prompt flags and flow; require explicit direct flags; remove recommendation subsystem; keep discovery/cache behavior.
- `tests/unit/cli/commands/test_codex_model_sync.py`: replace recommendation tests with manual selection, update prompt, direct flag, and discovery tests.
- `tests/unit/cli/commands/test_models.py`: update Codex parser expectations for removed `--yes` and new update flags.

## Validation Commands
- `uv run pytest tests/unit/cli/commands/test_codex_model_sync.py tests/unit/cli/commands/test_models.py`
- `uv run ruff check src/cli/commands/codex_model.py tests/unit/cli/commands/test_codex_model_sync.py tests/unit/cli/commands/test_models.py`
- `uv run ty check src/cli/commands/codex_model.py tests/unit/cli/commands/test_codex_model_sync.py tests/unit/cli/commands/test_models.py`

## Acceptance Criteria
- `respec-ai models codex --yes` is rejected by argparse.
- `respec-ai models codex` offers an update prompt before discovery.
- `--update-codex` runs `npm install -g @openai/codex` without prompting.
- `--no-update-codex` skips the update prompt and update command.
- Model options come only from discovered Codex models or discovery cache fallback.
- No Codex model recommendation or hardcoded-prior logic remains.
- Manual selection saves four Codex model tiers.
- Direct flags require all four tiers and save without prompting.

## Fresh Session Handoff Notes
- Keep `models opencode --yes` unchanged.
- Do not use OpenAI API/docs, Artificial Analysis, or local constants as available-model source.
