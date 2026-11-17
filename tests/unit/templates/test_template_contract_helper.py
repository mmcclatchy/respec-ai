"""Self-tests for the test-only template contract helper.

B10 and B11 (docs/phase-cooperative/phase-2-cooperative-flow.md) measure the phase
command through wait_sites() and touchpoint_steps(), and the invoked-vs-declared tool
check measures F12 through invoked_tools(). A helper that silently under-reports would
turn those guards vacuous, so each rule is pinned on a synthetic template here.
"""

from textwrap import dedent

import pytest

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter
from tests.support.template_contract import REPORT_HEADINGS, template_contract


def _guarded_flags(template: str) -> list[bool]:
    return [site.guarded for site in template_contract(dedent(template)).wait_sites()]


@pytest.mark.parametrize('guard', ['IF REPORT_DECISION == "failed":', 'ELIF BP_AVAILABLE is false:', 'ELSE:'])
def test_wait_under_a_condition_is_guarded(guard: str) -> None:
    template = f"""\
    ### Step 6: Briefing
    {guard}
      Ask the question.
      WAIT for the user response.
    """

    assert _guarded_flags(template) == [True]


def test_wait_at_the_top_of_a_step_is_unguarded() -> None:
    template = """\
    ### Step 6: Briefing
    Ask the question.
    WAIT for the user response.
    """

    assert _guarded_flags(template) == [False]


@pytest.mark.parametrize('loop', ['FOR each OD in OPEN_DECISIONS:', 'WHILE questions remain:', 'REPEAT until done:'])
def test_wait_under_a_loop_alone_is_unguarded(loop: str) -> None:
    template = f"""\
    ### Step 6: Briefing
    {loop}
      Ask the question.
      WAIT for the user response.
    """

    assert _guarded_flags(template) == [False]


def test_wait_under_a_loop_inside_a_condition_is_guarded() -> None:
    template = """\
    ### Step 11: Sign-off
    IF MATERIALIZE_RESULT has conflicts:
      FOR each CONFLICT in MATERIALIZE_RESULT.reconciliation_needed:
        Ask how to reconcile it.
        WAIT for the user response.
    """

    sites = template_contract(dedent(template)).wait_sites()

    assert [site.guards for site in sites] == [('IF MATERIALIZE_RESULT has conflicts:',)]


def test_wait_finds_its_condition_past_a_shallower_prose_line() -> None:
    template = """\
    ### Step 10: Design Review
    IF UNRESOLVED_CHECKS is not empty:
      Display the unresolved checks.
        Ask the user to send back or accept.
        WAIT for the user response.
    """

    assert _guarded_flags(template) == [True]


def test_sentence_case_prose_is_not_a_condition() -> None:
    template = """\
    ### Step 6: Briefing
    If the user has questions, answer them.
      WAIT for the user response.
    """

    assert _guarded_flags(template) == [False]


def test_a_condition_in_an_earlier_step_does_not_guard_a_later_wait() -> None:
    template = """\
    ### Step 5: Explore
    IF ARCHITECT_AGENT_ID is set:
      Resume the architect.
    ### Step 6: Briefing
      WAIT for the user response.
    """

    assert _guarded_flags(template) == [False]


def test_each_wait_is_attributed_to_the_step_it_sits_under() -> None:
    template = """\
    WAIT for the preamble response.
    ### Step 1: Parse User Inputs
    #### Step 1.3: Pick the phase file
    WAIT for the file choice.
    ### Step 10: Design Review (TOUCHPOINT)
    WAIT for the review choice.
    """

    sites = template_contract(dedent(template)).wait_sites()

    assert [(site.step, site.top_level_step) for site in sites] == [(None, None), ('1.3', '1'), ('10', '10')]


def test_every_wait_line_in_a_rendered_command_is_reported() -> None:
    template = TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.MARKDOWN, tui_adapter=ClaudeCodeAdapter()
    )
    wait_lines = [line.strip() for line in template.split('\n') if 'WAIT for' in line]

    assert wait_lines
    assert [site.line for site in template_contract(template).wait_sites()] == wait_lines


def test_touchpoint_steps_are_the_steps_whose_heading_carries_the_token() -> None:
    # TOUCHPOINT is a contract string: B10 counts the happy-path human stops by it.
    template = """\
    ### Step 5: Explore
    ### Step 6: Briefing (TOUCHPOINT)
    #### Step 6.1: Record the answers
    ### Step 10: Design Review (TOUCHPOINT)
    The next step is a TOUCHPOINT too.
    ### Step 11: Sign-off (TOUCHPOINT)
    """

    assert template_contract(dedent(template)).touchpoint_steps() == ['6', '10', '11']


@pytest.mark.parametrize('tool_name', ['AskUserQuestion', 'SendMessage'])
def test_a_tool_named_without_parentheses_counts_as_invoked(tool_name: str) -> None:
    # F12: these Claude Code tools are named in prose ("Use AskUserQuestion tool to present
    # options:"), never called as Name(...), so the parenthesis pattern alone misses them.
    template = f"""\
    ---
    allowed-tools: Bash, Read
    ---

    Use {tool_name} tool to continue.
    """

    contract = template_contract(dedent(template))

    assert tool_name.lower() in contract.invoked_tools()
    assert not contract.invoked_tools() <= contract.declared_tools()


def test_a_declared_bare_tool_satisfies_the_invoked_check() -> None:
    template = """\
    ---
    allowed-tools: Bash, AskUserQuestion, SendMessage
    ---

    Use AskUserQuestion tool to present options, then SendMessage to resume.
    """

    contract = template_contract(dedent(template))

    assert {'askuserquestion', 'sendmessage'} <= contract.invoked_tools() <= contract.declared_tools()


def test_guards_for_reports_the_conditions_around_every_line_naming_the_marker() -> None:
    template = dedent("""\
    STEP 0: Rehydrate
    CALL get_feedback
    IF NOTES is empty:
      CALL get_feedback
    """)

    assert template_contract(template).guards_for('CALL get_feedback') == [(), ('IF NOTES is empty:',)]


def test_findings_are_classified_by_the_tag_that_opens_them() -> None:
    template = dedent("""\
    - [mechanical] [Skeleton Index Module Mismatch - BLOCKING]: `a` is not in Module Layout
    - [judgment] [Unjustified Seam] CQ-001: `b` has one implementation
    - [Research Path Invalid - BLOCKING]: untagged
    """)
    contract = template_contract(template)

    assert contract.mechanical_findings() == {'skeleton-index-module-mismatch'}
    assert contract.judgment_findings() == {'unjustified-seam'}
    assert contract.blocker_conditions() == {'skeleton-index-module-mismatch', 'research-path-invalid'}


def test_report_format_is_the_fenced_block_that_opens_with_the_first_report_heading() -> None:
    template = dedent("""\
    ```markdown
    ## Some other example
    ```
        ```markdown
        ## For the user
        <summary>

        ## Decisions needed
        - None

        ## Research proposals
        - None

        ## Status
        - result: complete | needs-user | failed
        ```
    """)
    contract = template_contract(template)

    assert [line for line in contract.report_format() if line.startswith('## ')] == list(REPORT_HEADINGS)
    assert contract.report_section('## Research proposals') == ['- None']
    assert contract.report_section('## Status') == ['- result: complete | needs-user | failed']


def test_a_template_without_the_report_block_has_no_report_format() -> None:
    assert template_contract('```markdown\n## Status\n```\n').report_format() == []


def test_declared_inputs_are_the_bullets_under_the_named_heading_only() -> None:
    template = dedent("""\
    ### Scalar Inputs
    - loop_id: the loop
      - nested: not an input
    - review_round: the round
    ### Grouped Markdown Inputs
    - project_config_context_markdown: config
    """)
    contract = template_contract(template)

    assert contract.declared_inputs('### Scalar Inputs') == {'loop_id', 'review_round'}
    assert contract.declared_inputs('### Grouped Markdown Inputs') == {'project_config_context_markdown'}
    assert contract.declared_inputs('### Missing') == set()


_STEPPED_TEMPLATE = dedent("""\
---
allowed-tools: Bash
---
Overview text.
### Step 1: Parse User Inputs
#### Step 1.3: Pick the phase file
Pick it.
### Step 11: Sign-off (TOUCHPOINT)
Ask the remaining decisions.
#### Step 11.2: Materialize
Run the materializer.
### Step 12: Store and Hand Off
Store it.
""")


def test_step_numbers_lists_every_step_heading_in_reading_order() -> None:
    assert template_contract(_STEPPED_TEMPLATE).step_numbers() == ['1', '1.3', '11', '11.2', '12']


def test_preamble_is_everything_before_the_first_step_heading() -> None:
    preamble = template_contract(_STEPPED_TEMPLATE).preamble()

    assert 'Overview text.' in preamble
    assert 'Step 1' not in preamble


def test_step_section_spans_the_sub_steps_and_stops_at_the_next_step() -> None:
    section = template_contract(_STEPPED_TEMPLATE).step_section('11')

    assert 'Ask the remaining decisions.' in section
    assert 'Run the materializer.' in section
    assert 'Store it.' not in section


def test_step_section_does_not_treat_a_longer_number_as_a_sub_step() -> None:
    section = template_contract(_STEPPED_TEMPLATE).step_section('1')

    assert 'Pick it.' in section
    assert 'Ask the remaining decisions.' not in section


def test_step_section_of_a_missing_step_is_empty() -> None:
    assert template_contract(_STEPPED_TEMPLATE).step_section('7') == ''


def test_line_steps_attributes_every_line_to_the_heading_above_it() -> None:
    contract = template_contract(_STEPPED_TEMPLATE)
    lines = _STEPPED_TEMPLATE.split('\n')

    steps = dict(zip(lines, contract.line_steps(), strict=True))

    assert steps['Overview text.'] is None
    assert steps['Pick it.'] == '1.3'
    assert steps['Run the materializer.'] == '11.2'


def test_enclosing_at_reports_loops_as_well_as_conditions_within_the_step() -> None:
    template = dedent("""\
    ### Step 7: Run Approved Research
    FOR each item in RESEARCH_QUEUE:
      IF item.tier == "web-research":
        Dispatch it.
    ### Step 8: Draft
    Draft it.
    """)
    contract = template_contract(template)
    dispatch = template.split('\n').index('    Dispatch it.')

    assert contract.enclosing_at(dispatch) == (
        'IF item.tier == "web-research":',
        'FOR each item in RESEARCH_QUEUE:',
    )
    assert contract.guards_at(dispatch) == ('IF item.tier == "web-research":',)
    assert contract.enclosing_at(template.split('\n').index('Draft it.')) == ()


def test_block_sites_find_a_multi_line_block_whatever_its_indentation() -> None:
    block = 'Invoke: bp-pipeline\nInput:\n  - MODE: codegen'
    template = '\n'.join(
        [
            '### Step 7: Research',
            'Invoke: bp-pipeline',
            'Input:',
            '  - MODE: codegen',
            'FOR each item:',
            '    Invoke: bp-pipeline',
            '    Input:',
            '      - MODE: codegen',
            'Invoke: bp-pipeline',
            'Input:',
            '  - MODE: research',
        ]
    )

    assert template_contract(template).block_sites(block) == [1, 5]


def test_an_empty_block_has_no_sites() -> None:
    # resume_architect renders empty where a TUI cannot resume a subagent; it must not
    # match every blank line of the template.
    assert template_contract('### Step 5: Explore\n\nExplore.\n').block_sites('') == []


def test_decision_blocks_stop_at_the_branch_indentation() -> None:
    template = dedent("""\
    IF REPORT_DECISION == "failed":
      ERROR: "the architect failed: [detail]"
      EXIT: Workflow terminated
    Show the report.
    EXIT: unrelated
    ELIF REPORT_DECISION == "needs-user":
      Continue.
    """)

    blocks = template_contract(template).decision_blocks('failed')

    assert blocks == [
        'IF REPORT_DECISION == "failed":\n  ERROR: "the architect failed: [detail]"\n  EXIT: Workflow terminated'
    ]


def test_an_agent_declares_its_tools_on_the_frontmatter_tools_line() -> None:
    # Agent templates carry `tools:` where commands carry `allowed-tools:`; B16 (phase 3)
    # compares an agent's invoked MCP tools against it.
    template = dedent("""\
    ---
    name: respec-phase-critic
    tools: mcp__respec-ai__get_document, Read, Write(.respec-ai/plans/*/phases/*/implementation.md)
    ---

    CALL mcp__respec-ai__get_document(doc_type="phase")
    """)

    assert template_contract(template).declared_tools() == {'mcp__respec-ai__get_document', 'read', 'write'}


def test_a_tools_line_outside_the_frontmatter_declares_nothing() -> None:
    template = dedent("""\
    ---
    name: respec-phase-critic
    ---

    tools: mcp__respec-ai__store_document
    """)

    assert template_contract(template).declared_tools() == set()


def test_block_at_is_the_line_with_only_the_lines_indented_beneath_it() -> None:
    template = dedent("""\
    IF ARCHITECT_FINDINGS is not empty AND REPAIR_ROUNDS < 2:
      REPAIR_ROUNDS += 1

      Go to Step 9.
    LEFTOVERS = []
      continued
    """)

    assert template_contract(template).block_at(0) == (
        'IF ARCHITECT_FINDINGS is not empty AND REPAIR_ROUNDS < 2:\n  REPAIR_ROUNDS += 1\n\n  Go to Step 9.'
    )
