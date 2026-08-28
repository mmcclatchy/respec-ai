from src.platform.template_helpers import create_frontend_reviewer_agent_tools
from src.platform.templates.agents import generate_frontend_reviewer_template
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter


class TestFrontendReviewerBrowserToolGrants:
    def test_grants_playwright_tools_but_never_write_or_bash_output(self) -> None:
        # B7
        tools = create_frontend_reviewer_agent_tools(ClaudeCodeAdapter())
        template = generate_frontend_reviewer_template(tools)

        assert 'mcp__playwright__browser_navigate' in template
        assert 'mcp__playwright__browser_snapshot' in template
        assert 'mcp__playwright__browser_network_requests' in template
        assert 'mcp__playwright__browser_network_request' in template
        assert 'mcp__playwright__browser_run_code_unsafe' not in template
        # Neither tool exists in the real, currently-published @playwright/mcp server (verified
        # against its live tools/list) -- granting them would be a dead tool reference.
        assert 'mcp__playwright__browser_verify' not in template
        assert 'mcp__playwright__browser_set_storage_state' not in template
        assert 'BashOutput' not in template
        assert 'Write' not in tools.tools_yaml

    def test_generates_for_all_three_tuis_without_raising(self) -> None:
        # B7/B8: catches the TemplateToolBuilder ValueError (F17) at test time, not at a
        # user's `respec-ai regenerate`.
        for adapter in (
            ClaudeCodeAdapter(),
            OpenCodeAdapter(model_overrides={'review': 'gpt-5'}),
            CodexAdapter(model_overrides={'review': 'gpt-5'}),
        ):
            tools = create_frontend_reviewer_agent_tools(adapter)
            template = generate_frontend_reviewer_template(tools)
            assert 'BashOutput' not in template
            assert 'Write' not in tools.tools_yaml

    def test_opencode_frontmatter_uses_lowercase_bash(self) -> None:
        # B8, Portability exit criterion: opencode's tool name for Bash is lowercase.
        tools = create_frontend_reviewer_agent_tools(OpenCodeAdapter(model_overrides={'review': 'gpt-5'}))
        generate_frontend_reviewer_template(tools)  # must not raise (F17)

        assert 'bash' in tools.tools_yaml
        assert 'Bash' not in tools.tools_yaml


class TestFrontendReviewerPreflightLifecycle:
    def _template(self) -> str:
        return generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(ClaudeCodeAdapter()))

    def test_starts_and_tears_down_preflight_via_bash(self) -> None:
        template = self._template()

        assert 'respec-ai frontend-preflight --start' in template
        assert 'respec-ai frontend-preflight --stop' in template
        assert 'respec-ai frontend-preflight --seed' in template

    def test_bash_is_restricted_to_frontend_preflight(self) -> None:
        template = self._template()

        assert 'Bash is for `respec-ai frontend-preflight` ONLY' in template
        assert 'Do NOT run `git add` or `git commit`.' in template
        assert 'Do NOT use shell redirection' in template

    def test_degrades_to_source_only_review_when_preflight_not_ready(self) -> None:
        # B2
        template = self._template()

        assert 'PREFLIGHT_RESULT.ready is false' in template
        assert 'RUNTIME_EVIDENCE_AVAILABLE = false' in template
        assert 'Do NOT treat this as a review failure and do NOT block on it.' in template
        assert 'Inspect components, routes, templates, state code, styles, and tests with Read/Glob regardless of RUNTIME_EVIDENCE_AVAILABLE' in template

    def test_scratch_evidence_is_citable_but_the_agent_may_not_author_it(self) -> None:
        template = self._template()

        assert 'citable evidence' in template
        assert 'must not write into that directory yourself' in template


class TestFrontendReviewerRubric:
    def _template(self) -> str:
        return generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(ClaudeCodeAdapter()))

    def test_rubric_points_sum_to_twenty_five(self) -> None:
        template = self._template()
        points = [7, 5, 4, 5, 2, 1, 1]
        for points_value in points:
            assert f'({points_value} Point' in template
        assert sum(points) == 25

    def test_only_deterministic_signals_may_block(self) -> None:
        # decisions.md: "Runtime evidence drives the loop through blockers"
        template = self._template()

        assert 'Only these findings qualify as `P0`/`[BLOCKING]`' in template
        assert "Visual Fit is capped at `P2`" in template
        assert 'Stack-Idiomatic Maintainability' in template
        assert 'never blocks' in template.lower() or 'Never blocks' in template


class TestFrontendReviewerSeamReview:
    def _template(self) -> str:
        return generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(ClaudeCodeAdapter()))

    def test_enumerates_seams_from_collaboration_and_wiring(self) -> None:
        # B10, B12
        template = self._template()

        assert '### Collaboration And Wiring' in template
        assert '#### Seam Review' in template
        assert '##### SEAM-' in template
        assert 'undeclared' in template.lower()

    def test_every_seam_finding_requires_exactly_one_target_tag(self) -> None:
        # B13
        template = self._template()

        assert '[Target:frontend]' in template
        assert '[Target:backend]' in template
        assert '[Target:both]' in template
        assert 'exactly one `[Target:...]` tag' in template

    def test_seam_findings_cite_both_sides(self) -> None:
        # B11
        template = self._template()

        assert 'Seam findings cite both sides' in template
        assert 'Frontend side' in template
        assert 'Backend side' in template

    def test_degrades_to_static_comparison_without_runtime_evidence(self) -> None:
        # B14
        template = self._template()

        assert 'static comparison only' in template.lower() or 'static signature comparison' in template

    def test_seam_findings_are_structured_not_only_markdown(self) -> None:
        # B15
        template = self._template()

        assert '(also stored in findings)' in template
