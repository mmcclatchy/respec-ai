"""Behavior pins for phase 9 -- splitting the coder into frontend/backend agents.

See docs/frontend-refactor/phase-9-coder-split.md, behaviors B1-B12.
"""

from src.platform.models import PlatformType
from src.platform.template_generator import _AGENT_NAMES, _get_agent_specs, expected_agents_count
from src.platform.template_helpers import (
    create_coder_agent_tools,
    create_frontend_coder_agent_tools,
)
from src.platform.templates.agents import generate_coder_template, generate_frontend_coder_template
from src.platform.templates.agents.coder_contracts import (
    render_coder_handoff_contract,
    render_coder_ownership_boundary_contract,
)
from src.platform.templates.commands.code_command import generate_code_command_template
from src.platform.templates.commands.patch_command import generate_patch_command_template
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.template_helpers import create_code_command_tools, create_patch_command_tools


_adapter = ClaudeCodeAdapter()


class TestCoderRegistration:
    def test_both_coders_registered_in_agent_names(self) -> None:
        assert 'respec-coder' in _AGENT_NAMES
        assert 'respec-frontend-coder' in _AGENT_NAMES

    def test_agent_specs_include_both_coders_for_every_tui(self) -> None:
        opencode_overrides = {
            'reasoning': 'gpt-5',
            'orchestration': 'gpt-5',
            'coding': 'gpt-5',
            'review': 'gpt-5',
        }
        for adapter in (
            ClaudeCodeAdapter(),
            CodexAdapter(),
            OpenCodeAdapter(model_overrides=opencode_overrides),
        ):
            names = {spec.name for spec in _get_agent_specs(adapter, PlatformType.MARKDOWN)}
            assert 'respec-coder' in names
            assert 'respec-frontend-coder' in names
            assert len(names) == expected_agents_count(adapter)


class TestCoderTemplateSize:
    def test_backend_coder_template_is_reasonably_sized(self) -> None:
        # B8: neither coder template exceeds ~250 lines of domain content. The generated
        # template also embeds ~500 lines of contract text shared with the frontend coder,
        # so this asserts the *module* (not generated output) stays small.
        with open('src/platform/templates/agents/coder.py') as f:
            assert len(f.readlines()) < 250

    def test_frontend_coder_template_is_reasonably_sized(self) -> None:
        with open('src/platform/templates/agents/frontend_coder.py') as f:
            assert len(f.readlines()) < 250


class TestSharedContractReuse:
    def test_both_coders_share_the_handoff_contract_verbatim(self) -> None:
        # B6: same renderer, no duplicated fixtures.
        handoff = render_coder_handoff_contract()
        backend_template = generate_coder_template(create_coder_agent_tools(_adapter))
        frontend_template = generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter))

        assert handoff in backend_template
        assert handoff in frontend_template

    def test_both_coders_report_unrouted_findings_field(self) -> None:
        backend_template = generate_coder_template(create_coder_agent_tools(_adapter))
        frontend_template = generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter))

        assert 'Unrouted findings:' in backend_template
        assert 'Unrouted findings:' in frontend_template


class TestOwnershipBoundary:
    def test_backend_coder_acts_on_backend_and_both_ignores_frontend(self) -> None:
        template = generate_coder_template(create_coder_agent_tools(_adapter))

        assert 'Act ONLY on `[Target:backend]` and `[Target:both]` findings.' in template
        assert 'Ignore `[Target:frontend]` findings entirely' in template

    def test_frontend_coder_acts_on_frontend_and_both_ignores_backend(self) -> None:
        template = generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter))

        assert 'Act ONLY on `[Target:frontend]` and `[Target:both]` findings.' in template
        assert 'Ignore `[Target:backend]` findings entirely' in template

    def test_ownership_contract_renderer_swaps_only_the_domain_word(self) -> None:
        backend = render_coder_ownership_boundary_contract('backend')
        frontend = render_coder_ownership_boundary_contract('frontend')

        assert 'You are the backend coder.' in backend
        assert 'You are the frontend coder.' in frontend
        assert '[Target:backend]' in backend and '[Target:frontend]' in backend
        assert '[Target:backend]' in frontend and '[Target:frontend]' in frontend

    def test_untagged_review_cycle_finding_is_unroutable_not_adopted(self) -> None:
        for template in (
            generate_coder_template(create_coder_agent_tools(_adapter)),
            generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter)),
        ):
            assert 'is NOT yours by default' in template
            assert '`Unrouted findings` field' in template

    def test_standards_only_mode_routes_by_file_not_by_tag(self) -> None:
        # coding-standards-reviewer findings carry no [Target:...] tag (only review-cycle
        # reviewers tag findings), so standards-only mode must not treat them as unroutable.
        for template in (
            generate_coder_template(create_coder_agent_tools(_adapter)),
            generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter)),
        ):
            assert 'coding-standards-reviewer findings carry no `[Target:...]` tag' in template
            assert 'ownership here is by FILE, not by tag' in template

    def test_seam_conflict_with_collaboration_and_wiring_requires_amendment(self) -> None:
        # B12
        for template in (
            generate_coder_template(create_coder_agent_tools(_adapter)),
            generate_frontend_coder_template(create_frontend_coder_agent_tools(_adapter)),
        ):
            assert (
                'that is also a `DOCUMENT_AMENDMENT_REQUIRED` handoff, not\na unilateral fix'
                in template
            )


class TestCodeCommandDefaultDispatch:
    def test_backend_only_default_falls_back_when_step_domains_empty(self) -> None:
        # B1: a backend-only phase (or one where the Step scan finds nothing to classify)
        # must behave identically to the pre-split single-coder invocation -- i.e. dispatch
        # only the backend coder, unconditionally, rather than requiring a populated
        # STEP_DOMAINS to reach the backend branch at all.
        tools = create_code_command_tools(
            'mcp__linear-server__get_issue', 'mcp__linear-server__create_comment', PlatformType.LINEAR
        )
        template = generate_code_command_template(tools)

        assert 'ACTIVE_CODER_DOMAINS = set(STEP_DOMAINS.values()) if STEP_DOMAINS else {"backend"}' in template

    def test_frontend_and_backend_branches_are_independently_gated(self) -> None:
        # B2/B3: the backend and frontend invocations sit behind separate, independent IF
        # branches on ACTIVE_CODER_DOMAINS -- a frontend-only ACTIVE_CODER_DOMAINS reaches
        # only the frontend branch, and a mixed one reaches both, sequentially (never a
        # parallel fan-out, since coders may touch a shared file).
        tools = create_code_command_tools(
            'mcp__linear-server__get_issue', 'mcp__linear-server__create_comment', PlatformType.LINEAR
        )
        template = generate_code_command_template(tools)

        backend_idx = template.index('IF "backend" in ACTIVE_CODER_DOMAINS:')
        frontend_idx = template.index('IF "frontend" in ACTIVE_CODER_DOMAINS:')
        assert backend_idx < frontend_idx
        assert 'not invoked in parallel' in template or 'are not invoked in parallel' in template


class TestCodeCommandDispatch:
    def test_code_command_dispatches_both_coders_by_step_domain(self) -> None:
        tools = create_code_command_tools(
            'mcp__linear-server__get_issue', 'mcp__linear-server__create_comment', PlatformType.LINEAR
        )
        template = generate_code_command_template(tools)

        assert 'STEP_DOMAINS' in template
        assert 'ACTIVE_CODER_DOMAINS' in template
        assert 'IF "backend" in ACTIVE_CODER_DOMAINS:' in template
        assert 'IF "frontend" in ACTIVE_CODER_DOMAINS:' in template
        assert 'MERGED_CODER_REPORT' in template

    def test_code_command_still_computes_step_modes_for_reviewer_rostering(self) -> None:
        # Regression guard: STEP_DOMAINS is additive; STEP_MODES-driven reviewer rostering
        # (used by section 6.6) must be untouched by the coder-dispatch addition.
        tools = create_code_command_tools(
            'mcp__linear-server__get_issue', 'mcp__linear-server__create_comment', PlatformType.LINEAR
        )
        template = generate_code_command_template(tools)

        assert 'STEP_MODES = set()' in template
        assert 'IF "frontend" in STEP_MODES:' in template
        assert 'ACTIVE_REVIEWERS.append("frontend-reviewer")' in template


class TestPatchCommandDispatch:
    def test_patch_command_dispatches_both_coders_by_step_domain(self) -> None:
        platform_tools = ['mcp__linear-server__get_issue', 'mcp__linear-server__create_comment']
        tools = create_patch_command_tools(platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans')
        template = generate_patch_command_template(tools)

        assert 'STEP_DOMAINS' in template
        assert 'ACTIVE_CODER_DOMAINS' in template
        assert 'IF "backend" in ACTIVE_CODER_DOMAINS:' in template
        assert 'IF "frontend" in ACTIVE_CODER_DOMAINS:' in template
        assert 'MERGED_CODER_REPORT' in template

    def test_backend_only_default_falls_back_when_step_domains_empty(self) -> None:
        # B1, patch-command variant.
        platform_tools = ['mcp__linear-server__get_issue', 'mcp__linear-server__create_comment']
        tools = create_patch_command_tools(platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans')
        template = generate_patch_command_template(tools)

        assert 'ACTIVE_CODER_DOMAINS = set(STEP_DOMAINS.values()) if STEP_DOMAINS else {"backend"}' in template

    def test_patch_command_still_computes_step_modes_for_reviewer_rostering(self) -> None:
        # Regression guard mirroring the code-command test: STEP_DOMAINS is additive.
        platform_tools = ['mcp__linear-server__get_issue', 'mcp__linear-server__create_comment']
        tools = create_patch_command_tools(platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans')
        template = generate_patch_command_template(tools)

        assert 'STEP_MODES = set()' in template
        assert 'IF "frontend" in STEP_MODES:' in template
        assert 'ACTIVE_REVIEWERS.append("frontend-reviewer")' in template
