# Testing methodology for v2

Every change in this rework is built test-first, and every test pins a **behavior** rather than an
implementation detail. This document defines what that means concretely in this codebase, because the
distinction is genuinely hard here — respec-ai generates prompts, and prompts resist ordinary
behavioral testing unless you are deliberate about it.

Read this before writing tests for any phase.

## The cycle

For each unit of work in a phase document:

1. **Red** — write a test that names the behavior in its function name and fails for the right
   reason. Run it. Confirm the failure message describes the missing behavior, not a typo or an
   import error. A test that has never failed meaningfully has proven nothing.
2. **Green** — write the least code that makes it pass.
3. **Refactor** — clean up with the test as the safety net.

Phase 0 is unusual and valuable: several of its tests go red against *existing* code, so the red step
is free and the failure is real evidence of the bug. Take that seriously — it is the best proof
available that the test harness works before anything depends on it.

## The discriminating question

> If I reimplemented this a completely different way but kept the observable outcome identical, would
> this test still pass?

- **Yes** → behavior test. Keep it.
- **No** → implementation-detail test. Rewrite it, or delete it.

A second question that catches the subtler cases:

> If this test fails, does a *user* care?

If the only consequence of failure is "an internal name changed," it is not pinning a behavior.

## Naming

Test names state the behavior and the condition, not the function under test.

```python
# Implementation-detail naming
def test_store_phase_calls_model_dump(): ...
def test_phase_command_contains_wait_for(): ...
def test_header_field_mapping_has_22_entries(): ...

# Behavior naming
def test_roadmap_objectives_survive_agent_refinement(): ...
def test_workflow_waits_for_user_before_continuing_on_user_input(): ...
def test_phase_document_round_trips_without_losing_content(): ...
```

The name is the specification. If you cannot name the behavior without referring to a function name,
you are probably testing the wrong thing.

## Layer-by-layer guide

### Document models (`src/models/`)

**Behavior:** content survives a round trip; a malformed document is rejected with a useful reason; a
user's hand-written section is not silently discarded.

```python
# ✅ Behavior — survives any parser rewrite
def test_user_content_in_every_section_survives_round_trip(phase_with_all_sections):
    restored = Phase.parse_markdown(phase_with_all_sections.build_markdown())
    assert restored == phase_with_all_sections

def test_horizontal_rule_inside_a_section_does_not_truncate_it():
    ...

# ❌ Implementation detail — breaks on any refactor, catches no bug
def test_header_field_mapping_contains_module_layout():
    assert 'module_layout' in Phase.HEADER_FIELD_MAPPING
```

**The exception that earns its keep:** the heading-collision test (Phase 0) asserts a property of
`HEADER_FIELD_MAPPING` directly. That looks like an implementation-detail test but is not — finding
F7 means substring collisions cause *silent content loss*, and the property is the only place that
failure mode is checkable before it happens. Frame it as the behavior it prevents:

```python
def test_no_section_name_can_shadow_another_and_silently_swallow_content():
```

### State managers (`src/utils/state_manager/`)

**Behavior:** what you store is what you read back; roadmap intent survives agent writes.

```python
# ✅ Behavior — same test passes against in-memory and postgres
async def test_stored_phase_reads_back_with_every_field_intact(state_manager, fully_populated_phase):
    await state_manager.store_phase('plan', fully_populated_phase)
    assert await state_manager.get_phase('plan', fully_populated_phase.phase_name) == fully_populated_phase

async def test_roadmap_seeded_objectives_survive_an_agent_write(state_manager, phase):
    await state_manager.store_phase('plan', phase)
    await state_manager.store_phase('plan', phase.model_copy(update={'objectives': 'drifted'}))
    assert (await state_manager.get_phase('plan', phase.phase_name)).objectives == phase.objectives
```

Run the same behavioral suite against both backends via a parametrized fixture. That is what makes
the postgres UPSERT hazard (finding F13) catchable — a transposed positional parameter shows up as
"field A came back holding field B's value," which a field-by-field equality assertion catches and a
mock-based test never will.

**Do not mock the thing under test.** `pytest-mock` is for external boundaries, not for asserting
that your own code called its own method.

### Loop state (`src/utils/loop_state.py`)

Already the best-shaped layer in the project. Behavior is "given this history, the loop decides X."

```python
# ✅ Behavior
def test_loop_escalates_to_user_when_score_stops_improving(): ...
def test_loop_does_not_complete_while_blockers_are_unresolved(): ...

# ❌ Implementation detail
def test_decide_next_loop_action_checks_completion_before_stagnation(): ...
```

### Generated templates (`src/platform/templates/`) — the hard case

Templates are prompts. You cannot execute them, so the temptation is to grep for phrases — and that
produces tests that break on rewording and pass on genuinely broken output. Both failure directions
are bad.

**The approach: assert the contract, not the prose.** Build a small test-only helper that extracts
semantic structure from a generated template, and assert against that structure.

```
tests/support/template_contract.py     # test-only; no production import
```

It should expose enough to answer questions like:

- Which decision branches exist, and does a given branch block for user response?
- Which agents does this command invoke, and with which scalar inputs?
- Which MCP tools are referenced, and does the command's declared tool list actually include them?
- Which document sections does an agent claim to read?

Then tests read as behavior:

```python
# ✅ Behavior — survives rewording, catches a genuinely broken branch
def test_phase_workflow_waits_for_the_user_when_the_loop_requests_input(phase_command):
    branch = template_contract(phase_command).decision_branch('user_input')
    assert branch.blocks_for_user_response()
    assert branch.persists_user_feedback()

def test_every_tool_a_command_invokes_is_declared_in_its_allowed_tools(phase_command):
    contract = template_contract(phase_command)
    assert contract.invoked_tools() <= contract.declared_tools()

# ❌ Implementation detail — passes on broken output, fails on a reworded fix
def test_phase_command_contains_wait_for(phase_command):
    assert 'WAIT for' in phase_command
```

Note what the second example buys: it would have caught finding F20 (`Read()` called without the
capability declared) and finding F6 (`store_user_feedback` referenced by a branch that never had the
tool) as a *class* of bug, not two individual ones.

**Start the helper minimal.** Phase 0 needs decision branches and tool declarations, nothing more.
Grow it as later phases need it. Do not build a markdown framework up front.

**Where a string assertion is still legitimate:** when the exact string *is* the contract because
something downstream parses it. `#### Step N:` is scanned by `code_command.py:315`, so asserting that
format is behavioral — a reworded version genuinely breaks the consumer. Say so in a comment when you
do this, so the next reader knows it is deliberate rather than lazy.

### TUI adapters

**Behavior:** every TUI gets a working interaction, whatever mechanism it uses.

```python
# ✅ Behavior — the point of the abstraction (finding F18)
@pytest.mark.parametrize('adapter', [ClaudeCodeAdapter(), OpenCodeAdapter(), CodexAdapter()])
def test_user_selection_renders_a_usable_prompt_for_every_tui(adapter):
    rendered = render_phase_command(adapter)
    assert template_contract(rendered).decision_branch('user_input').blocks_for_user_response()

def test_codex_output_never_references_a_tool_codex_lacks(codex_artifacts):
    assert 'AskUserQuestion' not in codex_artifacts
```

### Skeleton generation (Phase 4) — genuinely executable

The most testable part of the whole rework. Do not waste it on string assertions.

```python
# ✅ Behavior — the actual promise of the feature
def test_generated_skeletons_type_check(tmp_project, skeleton_index):
    generate_skeletons(tmp_project, skeleton_index)
    assert run_mypy(tmp_project).returncode == 0

def test_generated_tests_fail_before_implementation(tmp_project, skeleton_index):
    generate_skeletons(tmp_project, skeleton_index)
    assert run_pytest(tmp_project).returncode != 0

def test_existing_source_file_is_never_overwritten(tmp_project):
    original = write_file(tmp_project / 'src/kb/client.py', IMPLEMENTED_SOURCE)
    generate_skeletons(tmp_project, index_naming(tmp_project / 'src/kb/client.py'))
    assert read_file(tmp_project / 'src/kb/client.py') == original
```

That third test is the one that matters most in the entire suite. A clobber destroys a user's working
code, and nothing downstream recovers it. Write it before the write path exists.

## Fixtures

Prefer fixtures that describe a *situation* over fixtures that describe a data shape:

```python
# ✅ Reads as a scenario
@pytest.fixture
def phase_with_settled_shape_and_unresolved_blockers(): ...

# ❌ Reads as a constructor
@pytest.fixture
def phase_with_seven_fields_set(): ...
```

Existing fixtures live in `tests/unit/models/conftest.py`. Extend them rather than duplicating; there
is already a `test_fixture_quality.py` guarding against fixture drift.

## What not to test

- That a constant has a particular value.
- That a private method was called.
- That a template contains a particular sentence, unless a consumer parses that sentence.
- Enum membership, unless absence causes a silent failure (findings F15, F16, F17 are the cases where
  it does — those are worth a test *named for the silent failure it prevents*).

## Per-phase expectation

Each phase document lists its behaviors to pin, in the order they should be written. Those lists are
the red step. If a behavior in that list has no failing test before implementation starts, the phase
is not being built test-first.
