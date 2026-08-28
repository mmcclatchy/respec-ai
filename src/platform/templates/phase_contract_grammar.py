"""Shared Skeleton Index / Test List placeholder grammar.

Both phase_architect.py (the agent that authors this content) and phase_command.py
(the orchestrator's own structure reference) showed this grammar to their reader
with independently-drifting text -- the same drift class as F1's three roster
copies and F14's second extension list. One source of truth here; each template
composes it into its own placeholder set.
"""

MODULE_LAYOUT_PLACEHOLDER = (
    '- `src/path/to/module.py` — owns [single responsibility]\n'
    '- `src/path/to/Component.tsx` — owns [single responsibility]'
)

SKELETON_INDEX_PLACEHOLDER = (
    '- `src/path/to/module.py` :: ClassName.method_name(arg: Type) -> ReturnType\n'
    '- `src/path/to/Component.tsx` :: ComponentName(props: PropsType) -> JSX.Element\n'
    '  (one line per public message — this is the durable contract the conformance'
    ' reviewer diffs against. Use the language that owns the path, per'
    ' project_config_context_markdown. Python: a non-builtin type MUST be a'
    ' fully-qualified dotted path, e.g. `list[kb.models.BestPractice]`, so'
    ' materialization can emit a real import. TypeScript: write the type exactly as'
    ' declared or imported in the file — import resolution is not inferred, so a'
    ' dotted-looking name is materialized verbatim, never treated as an import path.'
    ' Append `, async` for a coroutine method or async function.)'
)

TEST_LIST_PLACEHOLDER = (
    '- `tests/unit/path/test_module.py::test_observable_behavior_under_condition`\n'
    '- `tests/unit/path/Component.spec.ts::renders the empty state when there are no results`\n'
    '  (behaviors, not file names — see Testing Strategy for approach. Name each test'
    " the way its own language's tests read: pytest node-id style for Python, a plain"
    ' English behavior description for TypeScript describe/it-style tests.)'
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
