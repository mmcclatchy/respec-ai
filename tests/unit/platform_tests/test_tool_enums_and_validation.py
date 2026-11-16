"""Tests for tool enums and validation system."""

import json
import re
from pathlib import Path

import pytest

from src.cli.services.best_practices_preflight import _normalize_tui_name
from src.platform.adapters import get_platform_adapter
from src.platform.models import PhaseCommandTools, ToolReference
from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_generator import _parse_command_spec
from src.platform.startup_validation import (
    validate_external_platform_tools,
    validate_platform_adapters,
)
from src.platform.template_helpers import (
    TemplateToolBuilder,
    create_code_command_tools,
    create_phase_command_tools,
    create_patch_command_tools,
    create_plan_command_tools,
    create_plan_critic_agent_tools,
    create_roadmap_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
)
from src.platform.tool_enums import (
    BuiltInToolCapability,
    ExternalPlatformTool,
    RespecAIAgent,
    RespecAICommand,
    RespecAITool,
)


from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter, get_tui_adapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_selector import TuiType


class TestToolEnums:
    def test_external_platform_tool_values(self) -> None:
        assert ExternalPlatformTool.LINEAR_CREATE_ISSUE.value == 'mcp__linear-server__create_issue'
        assert ExternalPlatformTool.GITHUB_CREATE_ISSUE.value == 'mcp__github__create_issue'

    def test_builtin_tool_values(self) -> None:
        assert BuiltInToolCapability.READ.value == 'read'
        assert BuiltInToolCapability.WRITE.value == 'write'
        assert BuiltInToolCapability.EDIT.value == 'edit'
        assert BuiltInToolCapability.TASK.value == 'task'

    def test_respec_ai_tool_values(self) -> None:
        assert RespecAITool.INITIALIZE_REFINEMENT_LOOP.value == 'mcp__respec-ai__initialize_refinement_loop'
        assert RespecAITool.DECIDE_LOOP_NEXT_ACTION.value == 'mcp__respec-ai__decide_loop_next_action'

    def test_review_section_tool_values(self) -> None:
        assert RespecAITool.STORE_REVIEW_SECTION.value == 'mcp__respec-ai__store_review_section'
        assert RespecAITool.GET_REVIEW_SECTION.value == 'mcp__respec-ai__get_review_section'
        assert RespecAITool.LIST_REVIEW_SECTIONS.value == 'mcp__respec-ai__list_review_sections'


class TestToolReference:
    def test_tool_reference_render_without_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInToolCapability.READ)
        assert tool_ref.render() == 'read'

    def test_tool_reference_render_with_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInToolCapability.READ, parameters='.respec-ai/plans/*/phases/*.md')
        assert tool_ref.render() == 'read(.respec-ai/plans/*/phases/*.md)'

    def test_tool_reference_validation_file_operations(self) -> None:
        # Should work with valid path
        ToolReference(tool=BuiltInToolCapability.READ, parameters='.respec-ai/plans/*/phases/*.md')

        # Should fail with directory traversal
        with pytest.raises(ValueError, match='directory traversal'):
            ToolReference(tool=BuiltInToolCapability.READ, parameters='../../../etc/passwd')

    def test_tool_reference_validation_task_agent(self) -> None:
        # Should work with valid agent name
        ToolReference(tool=BuiltInToolCapability.TASK, parameters='phase-architect')

        # Should fail with invalid agent name
        with pytest.raises(ValueError, match='Agent name can only contain'):
            ToolReference(tool=BuiltInToolCapability.TASK, parameters='invalid@agent!')

    def test_tool_reference_external_tools(self) -> None:
        tool_ref = ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE)
        assert tool_ref.render() == 'mcp__linear-server__create_issue'

    def test_tool_reference_respec_ai_tools(self) -> None:
        tool_ref = ToolReference(tool=RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        assert tool_ref.render() == 'mcp__respec-ai__initialize_refinement_loop'


class TestTemplateHelpers:
    def test_template_tool_builder(self) -> None:
        builder = TemplateToolBuilder(ClaudeCodeAdapter())
        tools = (
            builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
            .add_respec_ai_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
            .build()
        )

        assert 'Task(respec-phase-architect)' in tools
        assert 'mcp__respec-ai__initialize_refinement_loop' in tools

    def test_template_tool_builder_yaml_rendering(self) -> None:
        builder = TemplateToolBuilder(ClaudeCodeAdapter())
        yaml_output = (
            builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
            .add_respec_ai_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
            .render_yaml_tools()
        )

        assert '- Task(respec-phase-architect)' in yaml_output
        assert '- mcp__respec-ai__initialize_refinement_loop' in yaml_output

    def test_create_phase_command_tools(self) -> None:
        # Simulate what TemplateCoordinator does for LINEAR platform
        tools = create_phase_command_tools(
            'mcp__linear-server__create_issue',
            'mcp__linear-server__get_issue',
            'mcp__linear-server__list_issues',
            PlatformType.LINEAR,
            plans_dir='~/.claude/plans',
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'Task(respec-phase-architect)' in tools.tools_yaml
        assert 'Task(bp-pipeline)' in tools.tools_yaml.split(', ')
        assert 'Task(bp)' not in tools.tools_yaml.split(', ')
        assert 'mcp__respec-ai__initialize_refinement_loop' in tools.tools_yaml
        assert 'mcp__linear-server__create_issue' in tools.tools_yaml
        assert tools.platform == PlatformType.LINEAR

    def test_create_phase_command_tools_grants_write_for_the_phase_disk_mirror(self) -> None:
        tools = create_phase_command_tools(
            'mcp__linear-server__create_issue',
            'mcp__linear-server__get_issue',
            'mcp__linear-server__list_issues',
            PlatformType.LINEAR,
            plans_dir='~/.claude/plans',
            tui_adapter=ClaudeCodeAdapter(),
        )

        assert 'Write(.respec-ai/plans/*/phases/*/*.md)' in tools.tools_yaml

    def test_create_plan_command_tools_includes_reference_write_without_ask_user(self) -> None:
        platform_tools = [
            'mcp__linear-server__create_project',
            'mcp__linear-server__get_project',
        ]

        tools = create_plan_command_tools(
            platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans', tui_adapter=ClaudeCodeAdapter()
        )

        assert 'AskUserQuestion' not in tools.tools_yaml
        assert 'Read' in tools.tools_yaml
        assert 'Write(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_roadmap_agent_tools_includes_reference_read_permission(self) -> None:
        tools = create_roadmap_agent_tools(ClaudeCodeAdapter(), plans_dir='~/.claude/plans')
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_roadmap_critic_tools_include_reference_read_permission(self) -> None:
        tools = create_roadmap_critic_agent_tools(ClaudeCodeAdapter())
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_plan_critic_tools_include_reference_read_permission(self) -> None:
        tools = create_plan_critic_agent_tools(ClaudeCodeAdapter())
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_code_command_tools_include_unrestricted_bash(self) -> None:
        platform_tools = [
            'mcp__linear-server__get_issue',
            'mcp__linear-server__create_comment',
        ]
        tools = create_code_command_tools(
            platform_tools[0],
            platform_tools[1],
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        assert 'Bash' in tools.tools_yaml

    def test_create_patch_command_tools_include_unrestricted_bash(self) -> None:
        platform_tools = [
            'mcp__linear-server__get_issue',
            'mcp__linear-server__create_comment',
        ]
        tools = create_patch_command_tools(
            platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans', tui_adapter=ClaudeCodeAdapter()
        )
        assert 'Bash' in tools.tools_yaml

    def test_create_code_command_tools_includes_ask_tool_only_when_adapter_supports_it(self) -> None:
        platform_tools = [
            'mcp__linear-server__get_issue',
            'mcp__linear-server__create_comment',
        ]
        claude_tools = create_code_command_tools(
            platform_tools[0],
            platform_tools[1],
            PlatformType.LINEAR,
            tui_adapter=ClaudeCodeAdapter(),
        )
        codex_tools = create_code_command_tools(
            platform_tools[0],
            platform_tools[1],
            PlatformType.LINEAR,
            tui_adapter=CodexAdapter(),
        )
        opencode_tools = create_code_command_tools(
            platform_tools[0],
            platform_tools[1],
            PlatformType.LINEAR,
            tui_adapter=OpenCodeAdapter(),
        )

        assert 'AskUserQuestion' in claude_tools.tools_yaml
        assert 'AskUserQuestion' not in codex_tools.tools_yaml
        assert 'AskUserQuestion' not in opencode_tools.tools_yaml
        assert 'question' in opencode_tools.tools_yaml

    def test_create_roadmap_tools_includes_ask_tool_only_when_adapter_supports_it(self) -> None:
        phase_retrieval_tool = 'mcp__linear-server__get_issue'
        phase_listing_tool = 'mcp__linear-server__list_issues'
        roadmap_platform_tools = [phase_retrieval_tool, phase_listing_tool]
        claude_roadmap_tools = create_roadmap_tools(
            roadmap_platform_tools, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter()
        )
        codex_roadmap_tools = create_roadmap_tools(
            roadmap_platform_tools, PlatformType.LINEAR, tui_adapter=CodexAdapter()
        )
        opencode_roadmap_tools = create_roadmap_tools(
            roadmap_platform_tools, PlatformType.LINEAR, tui_adapter=OpenCodeAdapter()
        )

        assert 'AskUserQuestion' in claude_roadmap_tools.tools_yaml
        assert 'AskUserQuestion' not in codex_roadmap_tools.tools_yaml
        assert 'question' in opencode_roadmap_tools.tools_yaml

    def test_template_tool_builder_renders_adapter_specific_builtin_names(self) -> None:
        claude_builder = TemplateToolBuilder(ClaudeCodeAdapter()).add_builtin_tool(
            BuiltInToolCapability.ASK_USER_QUESTION
        )
        opencode_builder = TemplateToolBuilder(OpenCodeAdapter()).add_builtin_tool(
            BuiltInToolCapability.ASK_USER_QUESTION
        )

        assert claude_builder.build() == ['AskUserQuestion']
        assert opencode_builder.build() == ['question']

    def test_template_tool_builder_rejects_unsupported_capability_for_adapter(self) -> None:
        builder = TemplateToolBuilder(CodexAdapter()).add_builtin_tool(BuiltInToolCapability.ASK_USER_QUESTION)

        with pytest.raises(ValueError, match='does not support built-in tool capability'):
            builder.build()


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_PHASE_TUIS = [
    ClaudeCodeAdapter(),
    OpenCodeAdapter(model_overrides=_HERMETIC_MODELS),
    CodexAdapter(model_overrides=_HERMETIC_MODELS),
]
_PHASE_TUI_IDS = ['claude-code', 'opencode', 'codex']
_PORTABLE_TUIS = _PHASE_TUIS[1:]
_PORTABLE_TUI_IDS = _PHASE_TUI_IDS[1:]

_INVOCATION_INPUT = re.compile(r'^\s*-\s*(?P<name>\w+):\s*(?P<value>.+?)\s*$', re.MULTILINE)
_RESUME_ADDRESSEE = re.compile(r'^\s*to:\s*(?P<addressee>\S+)\s*$', re.MULTILINE)

_AGENT_IDS = {'loop_id': 'LOOP_ID', 'plan_name': 'PLAN_NAME', 'phase_name': 'PHASE_NAME'}
_CONFIG_CONTEXT = {'project_config_context_markdown': 'PROJECT_CONFIG_CONTEXT_MARKDOWN'}

# Field names from bp-pipeline's published input interface
# (~/.config/best-practices-rag/references/bp-pipeline-interface.md), which bp-pipeline parses.
# These are the fields the orchestrator computes at dispatch time (phase 2 work item 6, Step 7).
_BP_PIPELINE_DISPATCH_FIELDS = frozenset(
    {
        'MODE',
        'TECH',
        'TOPICS',
        'QUERY',
        'PRIMARY_QUERY',
        'OUTPUT_FILE',
        'TECH_VERSIONS_JSON',
        'CUTOFF_DATE',
        'COVERED_TECHS',
        'UNCOVERED_TECH',
        'ALL_QUERIED_TECHS',
        'LANGUAGES',
        'LANGUAGE_AGNOSTIC',
    }
)


def _phase_command_tools(adapter: TuiAdapter, platform: PlatformType = PlatformType.MARKDOWN) -> PhaseCommandTools:
    platform_adapter = get_platform_adapter(platform)
    return create_phase_command_tools(
        platform_adapter.create_phase_tool,
        platform_adapter.retrieve_phase_tool,
        platform_adapter.list_phases_tool,
        platform,
        tui_adapter=adapter,
    )


def _invocation_inputs(invocation: str) -> dict[str, str]:
    return {match.group('name'): match.group('value') for match in _INVOCATION_INPUT.finditer(invocation)}


class TestPhaseCommandToolsForTheCooperativeFlow:
    @pytest.mark.parametrize('adapter', _PHASE_TUIS, ids=_PHASE_TUI_IDS)
    def test_phase_command_is_granted_bp_pipeline_and_never_the_unrunnable_bp(self, adapter: TuiAdapter) -> None:
        # B14 (F15): no agent named bp exists on any TUI; bp-pipeline is the dispatchable agent.
        granted = _phase_command_tools(adapter).tools_yaml.split(', ')

        assert 'Task(bp-pipeline)' in granted
        assert 'Task(bp)' not in granted

    def test_opencode_permits_the_phase_command_to_dispatch_bp_pipeline(self, tmp_path: Path) -> None:
        # B14: opencode turns a command's Task(...) grants into permission.task, which denies
        # every subagent the command does not name (README "bp invocation per TUI").
        adapter = OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
        template = TemplateCoordinator().generate_command_template(
            RespecAICommand.PHASE, PlatformType.MARKDOWN, tui_adapter=adapter
        )
        adapter.write_all(tmp_path, [], [_parse_command_spec(RespecAICommand.PHASE, template, 'model')])

        config = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
        task_permission = config['agent'][f'cmd-{RespecAICommand.PHASE.value}']['permission']['task']

        assert task_permission.get('bp-pipeline') == 'allow'
        assert 'bp' not in task_permission

    @pytest.mark.parametrize('adapter', _PHASE_TUIS, ids=_PHASE_TUI_IDS)
    def test_research_dispatch_names_bp_pipeline_exactly_with_every_field_it_computes(
        self, adapter: TuiAdapter
    ) -> None:
        # B14 (F15, F16): codex's respec-<x>-agent rename would dispatch an agent that does not exist.
        invocation = _phase_command_tools(adapter).invoke_bp_pipeline
        inputs = _invocation_inputs(invocation)

        assert 'bp-pipeline' in invocation
        assert 'respec-bp-pipeline' not in invocation
        assert _BP_PIPELINE_DISPATCH_FIELDS <= inputs.keys()
        assert inputs['MODE'] == 'codegen'

    @pytest.mark.parametrize('tui', list(TuiType))
    def test_bp_preflight_checks_the_installation_for_the_tui_the_workflow_runs_on(self, tui: TuiType) -> None:
        # B15: the command string is parsed by the best-practices-rag CLI, whose exit code is the
        # availability signal; it must check the same installation the init preflight checks.
        tools = _phase_command_tools(get_tui_adapter(tui))

        assert tools.bp_preflight_command == f'best-practices-rag check --tui {_normalize_tui_name(tui.value)}'

    @pytest.mark.parametrize('adapter', _PHASE_TUIS, ids=_PHASE_TUI_IDS)
    @pytest.mark.parametrize(
        ('field', 'mode'),
        [
            ('invoke_architect_explore', 'explore'),
            ('invoke_architect_draft', 'draft'),
            ('invoke_architect_revise', 'revise'),
        ],
    )
    def test_each_architect_mode_is_invoked_with_its_mode_ids_and_config_context_only(
        self, adapter: TuiAdapter, field: str, mode: str
    ) -> None:
        # README "Agents and modes": never pass conversation text. The workflow guidance reaches
        # the architect as round-0 feedback, so no invocation carries it.
        invocation = getattr(_phase_command_tools(adapter), field)

        assert 'respec-phase-architect' in invocation
        assert _invocation_inputs(invocation) == {'phase_mode': mode, **_AGENT_IDS, **_CONFIG_CONTEXT}

    @pytest.mark.parametrize('adapter', _PHASE_TUIS, ids=_PHASE_TUI_IDS)
    def test_critic_review_is_invoked_with_the_round_it_stores_under_and_the_config_context(
        self, adapter: TuiAdapter
    ) -> None:
        # B4 (F9): the critic stores each review under review_round, so every round is kept.
        # F22: the critic gets the project config context too.
        invocation = _phase_command_tools(adapter).invoke_critic_review

        assert 'respec-phase-critic' in invocation
        assert _invocation_inputs(invocation) == {
            'phase_mode': 'review',
            **_AGENT_IDS,
            'review_round': 'REVIEW_ROUND',
            **_CONFIG_CONTEXT,
        }

    def test_claude_code_resumes_the_recorded_architect_with_its_mode_and_ids_only(self) -> None:
        # B21 (F13): SendMessage resumes the same architect with its exploration intact; the
        # relay contract still forbids passing conversation text.
        tools = _phase_command_tools(ClaudeCodeAdapter())
        addressee = _RESUME_ADDRESSEE.search(tools.resume_architect)

        assert 'SendMessage' in tools.tools_yaml.split(', ')
        assert 'SendMessage' in tools.resume_architect
        assert addressee is not None
        assert addressee.group('addressee') == 'ARCHITECT_AGENT_ID'
        assert _invocation_inputs(tools.resume_architect) == {'phase_mode': 'ARCHITECT_MODE', **_AGENT_IDS}

    @pytest.mark.parametrize('adapter', _PORTABLE_TUIS, ids=_PORTABLE_TUI_IDS)
    def test_portable_tuis_re_engage_the_architect_fresh_and_never_mention_resuming(self, adapter: TuiAdapter) -> None:
        # B21 (F13): codex closes each subagent after harvest and opencode cannot resume one.
        tools = _phase_command_tools(adapter)

        assert tools.resume_architect == ''
        assert 'SendMessage' not in tools.tools_yaml

    def test_hand_edit_store_keeps_the_frozen_field_exception(self) -> None:
        # B25: a user's hand edit is theirs to make, frozen roadmap fields included; the
        # parameter name is the store_document MCP tool's own.
        store = _phase_command_tools(ClaudeCodeAdapter()).store_document_user_edit

        assert store.startswith(f'{RespecAITool.STORE_DOCUMENT.value}(')
        assert 'allow_frozen_field_edits=true' in store


class TestStartupValidation:
    def test_validate_external_platform_tools(self) -> None:
        result = validate_external_platform_tools()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['linear_tools_count'] > 0
        assert result['github_tools_count'] > 0

    def test_validate_platform_adapters(self) -> None:
        result = validate_platform_adapters()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['adapters_count'] == 3
        assert 'adapters' in result
        assert result['properties_per_adapter'] == 13
