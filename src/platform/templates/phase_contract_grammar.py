"""Shared Skeleton Index / Test List placeholder grammar.

Both phase_architect.py (the agent that authors this content) and phase_command.py
(the orchestrator's own structure reference) showed this grammar to their reader
with independently-drifting text -- the same drift class as F1's three roster
copies and F14's second extension list. One source of truth here; each template
composes it into its own placeholder set.
"""

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
    '- `<path to a test file>::<observable behavior under a condition>`\n'
    '  (behaviors, not file names — see Testing Strategy for approach. Take the test file'
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
