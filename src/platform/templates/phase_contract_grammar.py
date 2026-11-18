"""Shared phase-document and implementation.md grammar shown to the phase agents.

One source of truth for the forms the writing agents are taught, so their copies cannot drift
(the drift class of F1's three roster copies and F14's second extension list). Each template
composes these into its own text.
"""

from src.models.phase import Phase


MODULE_LAYOUT_PLACEHOLDER = (
    '- `<path to a source file>` — owns [single responsibility]\n'
    '- `<path to another source file>` — owns [single responsibility]'
)

SKELETON_INDEX_PLACEHOLDER = (
    '- `<path to a source file>` :: <Owner>.<member>(<params>) -> <Result>\n'
    '- `<path to a source file>` :: <member>(<params>) -> <Result>\n'
    '  (one line per public seam: every exported unit another module calls. This is the'
    ' durable contract the conformance reviewer diffs against. Every language uses this one'
    ' notation; drop `<Owner>.` for a unit with no owner. `<Owner>` and `<member>` are each one'
    ' plain identifier of letters, digits and underscores that does not start with a digit:'
    ' write a qualified owner as its last segment only, and write any other character in a name'
    ' as an underscore. Only `<params>` and `<Result>` are'
    ' written in the syntax of the language that owns the path. Never write a native'
    ' declaration: materialization parses this notation and rejects anything else.'
    ' Language-specific rules come from `### Language Authoring Notes` in'
    ' project_config_context_markdown. Append `, async` for an asynchronous member.)'
)

TEST_LIST_PLACEHOLDER = (
    '- `<path to a test file>::<observable behavior under a condition>` — T-<n>\n'
    '  (behaviors, not file names. The T-<n> ID goes after the closing backtick and is never'
    ' renumbered or reused. Take the test file'
    ' location and the name form from the `[testing]` `location` and `naming` values of the'
    " owning language's standards TOML in project_config_context_markdown, and follow that"
    " language's section of `### Language Authoring Notes`.)"
)

UX_CONTRACT_PLACEHOLDER = (
    '#### UX Contract\n\n'
    '##### Route Index\n'
    '- `/path` :: [purpose] :: auth=none|session|role:<name>\n\n'
    '##### Required States\n'
    '- `/path` — loading: [observable assertion]; empty: [observable assertion]; error:'
    ' [observable assertion]; success: [observable assertion]; validation: [observable'
    ' assertion]\n\n'
    '##### Interaction Flows\n'
    '- FLOW-1: [step] → [step] → [step] — **Pass:** [mechanically checkable condition —'
    ' never "the page looks right" or "works correctly"; e.g. "submitting an invalid'
    ' email shows an inline error and the form is not cleared"]\n\n'
    '##### Accessibility Requirements\n'
    '- Conformance target: [e.g. WCAG 2.1 AA]\n'
    '- Keyboard paths: [which flows must complete without a mouse]\n'
    '- Focus order: [expected tab order for the interactive elements above]\n'
    '- Landmark and heading structure: [expected regions and heading levels]\n'
    '- Contrast: [minimum ratio, or "inherits from Design Source"]\n\n'
    '##### Breakpoints\n'
    '- `<name>` (`<width>px`): [what changes at this width]\n\n'
    '##### Design Source\n'
    '- [Claude Design handoff bundle path, design tokens file, or existing components'
    ' to match — read-only reference, never authored here]'
)

SUCCESS_CRITERION_PLACEHOLDER = '- SC-<n>: <measurable outcome> — measure: <a [commands] value or an observable check>'

# Phase 1's marker for a language with no usable configured command. The structural checks never
# flag a command that starts with "ask user", and the implementing agent asks for the command.
ASK_USER_COMMAND_MARKER = (
    'ask user — no test command configured for <language>;'
    ' set [commands].test in .respec-ai/config/standards/<language>.toml'
)

# The critic opens its stored Assessment Summary with one of these. get_feedback shows that summary
# as the first line under each iteration heading, so the finalizer acts only on brief reviews.
DESIGN_REVIEW_TAG = 'Review target: design'
BRIEF_REVIEW_TAG = 'Review target: brief'

# The phase.md sections the user approved at design review. The finalizer reproduces them verbatim,
# and the brief review compares them with the approved copy, so both name this one list.
REVIEWED_PHASE_SECTIONS = (
    'the Overview, Module Layout, Skeleton Index, Collaboration And Wiring, Test List, Design Shape -'
    ' Additional Sections (Design Narrative and UX Contract), Design Decisions, Delegation Bounds,'
    ' Implementation Plan References and Research Requirements'
)

# A Reviewed Section Changed finding quotes the approved text on its one blocker line: get_feedback
# flattens a multi-line bullet and splits its nested bullets into separate blockers.
QUOTED_LINE_BREAK = '⏎'

_GROUNDING_PLACEHOLDER = (
    '### Build on\n'
    '- `<path to code this phase extends>` — extend: <what and why> — informs: Step 2, Step 3\n'
    '### Leave alone\n'
    '- `<path that must not change>` — <why>\n'
    '### Exemplars\n'
    '- `<path to a file to imitate>` — imitate for <pattern> — informs: Step 1\n'
    '### Conventions\n'
    "- `<path to the project's standards config, contributor guide or lint config>` — governs <what>\n"
    '### Research to read\n'
    '- `.best-practices/<file>.md` — informs: SD-2, Step 3 — Source: RP-002'
)

_DELEGATION_BOUNDS_PLACEHOLDER = (
    '### Out of scope\n'
    "- <anti-requirement, from the Overview's Scope and the plan>\n"
    "### Implementer's discretion\n"
    '- <what an implementing agent decides without asking>\n'
    '### Escalate if\n'
    '- <condition that requires stopping to ask the user>'
)

_BEHAVIORS_AND_ACCEPTANCE_PLACEHOLDER = (
    '- Objective: <objective> → tests: T-1, T-3 → accepted by: SC-1\n'
    '- Scope item: <scope item> → tests: T-2 → accepted by: SC-1\n'
    '- Deliverable: <deliverable> → tests: T-4 → accepted by: SC-2\n'
    '### Not covered by tests\n'
    '- SC-3 — verified by <how>, when <when>'
)

_GUARDRAILS_PLACEHOLDER = (
    '### Invariants\n'
    '- G-1: <must always hold, or must never happen>\n'
    '### Error policy\n'
    '- G-2: <how errors are surfaced, propagated or recovered>\n'
    '### Security and performance\n'
    '- G-3: <constraint> (target: SC-3)\n'
    '### Deviation protocol\n'
    "- When the repository contradicts this brief, stop the step and add a line under implementation.md's"
    ' `## Deviations`, numbered from DEV-1 up, in the form'
    ' `- DEV-<n> | Step <N> | expected: … | found: … | action: …`. Continue only if the deviation stays'
    " within `### Implementer's discretion`; otherwise escalate."
)

BRIEF_SECTION_PLACEHOLDERS: dict[str, str] = dict(
    zip(
        Phase.BRIEF_SECTIONS,
        (
            _GROUNDING_PLACEHOLDER,
            _DELEGATION_BOUNDS_PLACEHOLDER,
            _BEHAVIORS_AND_ACCEPTANCE_PLACEHOLDER,
            _GUARDRAILS_PLACEHOLDER,
        ),
        strict=True,
    )
)

_STEP_VERIFY_PLACEHOLDER = "<the [commands].test value of the language that owns this step's files>"

# implementation.md is not a DocumentType, so this is a plain string. Its commands stay placeholders
# on purpose: the structural checks flag each one, so an agent that copies one unchanged is caught.
IMPLEMENTATION_BRIEF_EXAMPLE = f"""# Implementation Plan: phase-2-core-implementation

## Start here
### Prerequisites
- Sign-off wrote a skeleton for each Skeleton Index path of a language that has a materializer, and a failing test for each of its Test List entries: a `create` item that exists is that skeleton; fill it in and keep its signatures — check: `<path to the repository query module>`
### Required reading
- phase.md: Delegation Bounds; Guardrails; SD-1; Grounding § Exemplars
### First action
- Fill in the `<path to the repository query module>` skeleton (Step 1)

## Build Order
### Staging
Step 1 proves the query path before anything builds on it. Steps 2 and 3 each depend only on
Step 1, so they run in parallel (per plan reference: `<plans-dir>/<plan-name>.md` § "Section Name").

### Steps
#### Step 1: Query Path
- **Goal:** The service answers a query through the repository, end to end.
- **Context:** SD-1, G-1, `<path to the repository query module>` :: Repository.query, exemplar `<path to an existing query module>`, (per research: <pattern> from `.best-practices/<file>.md`)
- **Files:** create `<path to the repository query module>`; create `<path to the query test file>`; modify `<path to the service wiring module>`
- **Depends on:** none
- **Tests to turn green:** T-1, T-2
- **Verify:** `{_STEP_VERIFY_PLACEHOLDER}`
- **Done when:** T-1 and T-2 pass.

#### Step 2: Cache Layer
- **Goal:** A repeated query is served from a cache in front of the repository.
- **Context:** SD-1, G-2, `<path to the cache module>` :: QueryCache.get
- **Files:** create `<path to the cache module>`; create `<path to the cache test file>`
- **Depends on:** Step 1
- **Tests to turn green:** T-3
- **Verify:** `{_STEP_VERIFY_PLACEHOLDER}`
- **Done when:** T-3 passes and a repeated query never reaches the repository.

#### Step 3: Result List
- **Goal:** Query results render as a list.
- **Context:** SC-2, `<path to the result list component>` :: ResultList.render
- **Files:** create `<path to the result list component>`; create `<path to the result list test file>`
- **Depends on:** Step 1
- **Tests to turn green:** T-4
- **Verify:** `{_STEP_VERIFY_PLACEHOLDER}`
- **Done when:** T-4 passes.

## Policy
### Execution Intent Policy
- Mode: MVP
- Source: plan-default
- Tie-Break Policy: Prioritize core functional/spec delivery; defer non-P0 hardening gaps.

### Deferred Risk Register
- DR-001 | status=accepted | severity=P2 | scope=global | reason=Cache invalidation hardening deferred to post-MVP

## Checklist
- [ ] Implement the repository query (Step 1) (verify: {_STEP_VERIFY_PLACEHOLDER})
- [ ] Add the cache layer (Step 2) (verify: {_STEP_VERIFY_PLACEHOLDER})
- [ ] Implement the result list (Step 3) (verify: {_STEP_VERIFY_PLACEHOLDER})

## Exit criteria
- `<each [commands] value that verifies the whole phase>` passes
- every T-n in phase.md's Test List passes
- every SC-n holds as its measure states

## Deviations
- None
"""
