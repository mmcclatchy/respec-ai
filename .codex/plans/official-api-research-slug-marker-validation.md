# Official API Research and Slug Marker Validation

## Objective
Ground external API phase planning in official API documentation through `best-practices-rag`, using procedural slug markers only as candidate filters and content validation as the authority.

## Checklist
- [x] Update `phase_architect.py` to require official API research with `apidocs` and `apiintegration` marker topics.
- [x] Update `phase_command.py` Step 7.5 to synthesize official API prompts and stop using API-name filename matches as sufficient coverage.
- [x] Update `phase_critic.py` to require marker-filtered candidate docs plus content validation.
- [x] Add/update template tests for architect, command, and critic behavior.
- [x] Run targeted template tests and `git diff --check`.

## Acceptance Criteria
- Phase architect does not prefer SDKs globally; it asks research to decide SDK/client vs direct HTTP.
- Phase command API auto-synthesis prompt includes `apidocs apiintegration`.
- Phase command/critic no longer accept filename-only API-name matches as valid API doc coverage.
- Phase critic requires both marker-based candidate discovery and content validation.
