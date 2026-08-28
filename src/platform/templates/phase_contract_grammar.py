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
