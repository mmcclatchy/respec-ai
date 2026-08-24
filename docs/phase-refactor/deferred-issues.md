# Deferred issues

A running log of small, real issues found while implementing a phase that were deliberately **not**
fixed at the time — because fixing them was out of that phase's scope, unrelated to what it touches,
or would have expanded the diff beyond what the phase document called for. This is not a bug tracker
for the phases themselves (each phase document tracks its own *Behaviors to pin* and exit criteria) —
it exists so small out-of-scope findings don't get lost between sessions the way `findings.md` records
were lost before this rework started.

**When to add an entry:** you're implementing or reviewing a phase, you notice something wrong or
worth cleaning up, and fixing it now would mean touching code the current phase document doesn't
claim. Log it here instead of fixing it inline or letting it evaporate at the end of the session.

**When to remove an entry:** once fixed, delete the row rather than marking it done — this file should
only ever list live debt. If the fix needs its own commit message context, that belongs in git
history, not here.

**Format:**

| Found in | Location | Issue | Why deferred |
|---|---|---|---|
| Phase N — short phase name | `file.py:line` or `file.py` (function/section) | One or two sentences: what's wrong, concretely | Why it wasn't fixed as part of that phase's work |

---

## Open

| Found in | Location | Issue | Why deferred |
|---|---|---|---|
| Phase 3 — human gate | `src/platform/templates/agents/phase_architect.py` (`SOURCE 2`/`SOURCE 3` of `MANDATORY CONSTRAINT PRIORITY PROTOCOL`, search `(legacy)` and `backward compatibility`) | Fallback parsing for an older `"Claude Plan:"` strategic-plan-reference marker and an ad-hoc directive format, kept alongside the current `"Plan Reference:"` format. This project has no users and no backwards-compatibility requirement, so there's no one for this fallback to serve. | Predates Phase 3 and isn't part of its diff; removing it means auditing every caller of that constraint-parsing path, which is unrelated to the human-gate work Phase 3 was scoped to. |

## Fixed (kept briefly for continuity, then removed)

*(empty — entries move here only if you want a paper trail across one hand-off; otherwise delete
outright once fixed)*
