import re

from src.platform.tui_adapters import ClaudeCodeAdapter
from src.platform.template_helpers import (
    create_automated_quality_checker_agent_tools,
    create_backend_api_reviewer_agent_tools,
    create_code_quality_reviewer_agent_tools,
    create_coding_standards_reviewer_agent_tools,
    create_coder_agent_tools,
    create_database_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
)
from src.platform.templates.agents import (
    generate_automated_quality_checker_template,
    generate_backend_api_reviewer_template,
    generate_code_quality_reviewer_template,
    generate_coding_standards_reviewer_template,
    generate_coder_template,
    generate_database_reviewer_template,
    generate_frontend_reviewer_template,
    generate_infrastructure_reviewer_template,
    generate_spec_alignment_reviewer_template,
)


_adapter = ClaudeCodeAdapter()

_BANNED_ACTION_PATTERNS = (
    re.compile(r'\bshould\b', re.IGNORECASE),
    re.compile(r'\bconsider\b', re.IGNORECASE),
    re.compile(r'\bthink about\b', re.IGNORECASE),
    re.compile(r'\btry to\b', re.IGNORECASE),
    re.compile(r'\byou will\b', re.IGNORECASE),
    re.compile(r'\byour role is\b', re.IGNORECASE),
    re.compile(r'\bmay\b', re.IGNORECASE),
    re.compile(r'\bcan\b', re.IGNORECASE),
)

_REVIEW_ACTION_SECTION_TOKENS = (
    'TASKS:',
    '## MODE-AWARE REVIEW CONTRACT',
    '## PROJECT CONFIGURATION',
    '## ASSESSMENT',
    '## REVIEWER FEEDBACK MARKDOWN FORMAT',
    '## WORKFLOW',
    '## TDD METHODOLOGY',
    '## FEEDBACK INTEGRATION',
    '## ITERATION STRATEGY',
    'MANDATORY ',
)


def _extract_actionable_sections(template: str, section_tokens: tuple[str, ...]) -> str:
    actionable_lines: list[str] = []
    active = False
    in_fence = False
    fence_lang = ''

    for line in template.splitlines():
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_fence:
                in_fence = False
                fence_lang = ''
            else:
                in_fence = True
                fence_lang = stripped.removeprefix('```').strip().lower()
            continue

        if stripped.startswith('#'):
            active = any(token in stripped for token in section_tokens)
        elif any(token in stripped for token in section_tokens):
            active = True
        elif stripped.startswith('VIOLATION:'):
            active = True
        elif re.match(r'^(STEP|SUB-STEP)\b', stripped):
            active = True

        include_fence_line = in_fence and fence_lang in ('', 'text')
        if active and stripped and (not in_fence or include_fence_line):
            actionable_lines.append(stripped)

    return '\n'.join(actionable_lines)


def _assert_no_soft_action_language(template: str, section_tokens: tuple[str, ...]) -> None:
    actionable = _extract_actionable_sections(template, section_tokens)
    offenders = []
    for line in actionable.splitlines():
        if any(pattern.search(line) for pattern in _BANNED_ACTION_PATTERNS):
            offenders.append(line)
    assert not offenders, f'Found soft or ambiguous action language: {offenders}'


def test_review_actionable_section_extraction_includes_text_fences_but_skips_markdown_examples() -> None:
    template = """TASKS:
```text
This should be flagged.
```
## REVIEWER FEEDBACK MARKDOWN FORMAT
```markdown
This should stay ignored.
```
"""

    actionable = _extract_actionable_sections(template, _REVIEW_ACTION_SECTION_TOKENS)

    assert 'This should be flagged.' in actionable
    assert 'This should stay ignored.' not in actionable


def test_implementation_and_review_agents_retrieve_task_by_task_loop_id() -> None:
    templates = [
        generate_coder_template(
            create_coder_agent_tools(_adapter, platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'])
        ),
        generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
        generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
        generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
        generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
        generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
        generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
        generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
        generate_coding_standards_reviewer_template(create_coding_standards_reviewer_agent_tools(_adapter)),
    ]

    for template in templates:
        assert 'mcp__respec-ai__get_document(doc_type="task", loop_id={TASK_LOOP_ID})' in template
        assert 'mcp__respec-ai__get_document(doc_type="task", loop_id={PLANNING_LOOP_ID})' not in template


class TestAutomatedQualityCheckerTemplate:
    def test_template_structure(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        assert '---' in template
        assert 'name: respec-automated-quality-checker' in template
        assert 'model: sonnet' in template
        assert 'tools:' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_project_configuration(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        assert 'PROJECT CONFIGURATION' in template
        assert '.respec-ai/config/stack.toml' in template
        assert '.respec-ai/config/standards/*.toml' in template

    def test_template_includes_scoring(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        assert 'Tests Passing' in template
        assert 'Type Checking' in template
        assert 'Linting' in template
        assert 'Coverage' in template
        assert '50 Points Total' in template

    def test_template_has_mcp_tools(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        assert 'mcp__respec-ai__get_document' in template
        assert 'mcp__respec-ai__store_reviewer_result' in template

    def test_template_no_hardcoded_python_tools(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        # Should not contain hardcoded tool names as commands
        assert 'Run pytest' not in template
        assert 'Run mypy' not in template
        assert 'Run ruff' not in template


class TestSpecAlignmentReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_spec_alignment_reviewer_agent_tools(_adapter)
        template = generate_spec_alignment_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-spec-alignment-reviewer' in template
        assert 'model: sonnet' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_alignment_scoring(self) -> None:
        tools = create_spec_alignment_reviewer_agent_tools(_adapter)
        template = generate_spec_alignment_reviewer_template(tools)

        assert 'Phase Alignment' in template
        assert 'Requirements' in template
        assert '50 Points Total' in template


class TestFrontendReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_frontend_reviewer_agent_tools(_adapter)
        template = generate_frontend_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-frontend-reviewer' in template
        assert 'model: sonnet' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_accessibility(self) -> None:
        tools = create_frontend_reviewer_agent_tools(_adapter)
        template = generate_frontend_reviewer_template(tools)

        assert 'accessibility' in template.lower() or 'Accessibility' in template


class TestBackendApiReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_backend_api_reviewer_agent_tools(_adapter)
        template = generate_backend_api_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-backend-api-reviewer' in template
        assert 'model: sonnet' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_api_design(self) -> None:
        tools = create_backend_api_reviewer_agent_tools(_adapter)
        template = generate_backend_api_reviewer_template(tools)

        assert 'API' in template
        assert 'validation' in template.lower() or 'Validation' in template


class TestDatabaseReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_database_reviewer_agent_tools(_adapter)
        template = generate_database_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-database-reviewer' in template
        assert 'model: sonnet' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_schema_review(self) -> None:
        tools = create_database_reviewer_agent_tools(_adapter)
        template = generate_database_reviewer_template(tools)

        assert 'Schema' in template or 'schema' in template
        assert 'Migration' in template or 'migration' in template


class TestInfrastructureReviewerTemplate:
    def test_template_structure(self) -> None:
        tools = create_infrastructure_reviewer_agent_tools(_adapter)
        template = generate_infrastructure_reviewer_template(tools)

        assert '---' in template
        assert 'name: respec-infrastructure-reviewer' in template
        assert 'model: sonnet' in template
        assert '## Invocation Contract' in template
        assert 'TASKS:' in template

    def test_template_includes_container_review(self) -> None:
        tools = create_infrastructure_reviewer_agent_tools(_adapter)
        template = generate_infrastructure_reviewer_template(tools)

        assert 'Docker' in template or 'container' in template.lower()


class TestCodingStandardsTemplate:
    def test_coding_standards_phase2_feedback_preserves_blocking_markers(self) -> None:
        tools = create_coding_standards_reviewer_agent_tools(_adapter)
        template = generate_coding_standards_reviewer_template(tools)
        assert 'Preserve `[BLOCKING]` or `[Severity:P0]` markers in findings for critical violations.' in template


class TestReviewAgentConsistency:
    def test_all_review_agents_use_sonnet(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
        ]

        for template in templates:
            assert 'model: sonnet' in template

    def test_all_review_agents_have_required_sections(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
        ]

        for template in templates:
            assert 'name:' in template
            assert 'description:' in template
            assert '## Invocation Contract' in template
            assert 'TASKS:' in template

    def test_no_review_agent_contains_behavioral_descriptions(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
        ]

        behavioral_patterns = [
            'You will analyze',
            'Your role is',
            'You should consider',
            'Think about',
            'Consider different approaches',
        ]

        for template in templates:
            for pattern in behavioral_patterns:
                assert pattern not in template, f'Template contains behavioral description: {pattern}'

    def test_reviewers_enforce_mode_aware_severity_scope_contract(self) -> None:
        reviewer_templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
            generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
        ]
        for template in reviewer_templates:
            assert 'MODE-AWARE REVIEW CONTRACT (MANDATORY)' in template
            assert '[Severity:P0]' in template
            assert '[Scope:changed-file]' in template
            assert 'Deferred Risk Register' in template

    def test_shared_agents_use_single_workflow_guidance_contract(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
            generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
            generate_coder_template(
                create_coder_agent_tools(_adapter, platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'])
            ),
            generate_coding_standards_reviewer_template(create_coding_standards_reviewer_agent_tools(_adapter)),
        ]
        for template in templates:
            assert '## Invocation Contract' in template
            assert 'optional_context:' not in template
            assert 'request_brief:' not in template
            assert 'Do NOT reinterpret ambiguous guidance or invent missing requirements' in template

    def test_shared_agents_document_grouped_markdown_contracts(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
            generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
        ]
        for template in templates:
            assert 'workflow_guidance_markdown' in template
            assert '## Workflow Guidance' in template
            assert '### Guidance Summary' in template
            assert '### Constraints' in template
            assert '### Resume Context' in template
            assert '### Settled Decisions' in template


class TestCoderTemplateConfig:
    def test_coder_template_has_project_configuration(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'PROJECT CONFIGURATION' in template
        assert '.respec-ai/config/stack.toml' in template
        assert '.respec-ai/config/standards/*.toml' in template
        assert 'project_config_context_markdown' in template
        assert '.respec-ai/config/standards/guides/*.md' in template

    def test_coder_template_no_pseudocode_remains(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'TOOLS.test_runner' not in template
        assert 'TOOLS.test_command' not in template
        assert 'CONFIG = Read' not in template
        assert 'TOOLING[LANGUAGE]' not in template

    def test_quality_checker_template_no_pseudocode_remains(self) -> None:
        tools = create_automated_quality_checker_agent_tools(_adapter)
        template = generate_automated_quality_checker_template(tools)

        assert 'TOOLS.test_runner' not in template
        assert 'CONFIG = Read' not in template
        assert 'TOOLING[LANGUAGE]' not in template

    def test_coder_template_removes_agent_owned_commit_execution(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'git commit --no-verify -m' not in template
        assert 'Commit After Each Iteration' not in template
        assert 'Do NOT run git commit commands.' in template

    def test_coder_template_requires_structured_iteration_handoff(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert '## ITERATION HANDOFF OUTPUT FORMAT' in template
        assert '## Iteration Handoff' in template
        assert 'Mode: [normal|standards-only]' in template

    def test_coder_template_removes_orchestration_aware_wording(self) -> None:
        tools = create_coder_agent_tools(
            _adapter,
            platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'],
        )
        template = generate_coder_template(tools)

        assert 'Main command owns git commit execution' not in template
        assert 'Main Agent review' not in template

    def test_coding_standards_reviewer_rejects_guide_markdown_scoring_authority(self) -> None:
        tools = create_coding_standards_reviewer_agent_tools(_adapter)
        template = generate_coding_standards_reviewer_template(tools)
        assert 'Ignore `.respec-ai/config/standards/guides/*.md` for scoring' in template
        assert 'VIOLATION: Using guide markdown content as scoring authority.' in template

    def test_shared_review_and_coder_templates_use_imperative_language_in_actionable_sections(self) -> None:
        templates = [
            generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
            generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
            generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)),
            generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
            generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
            generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
            generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
            generate_coding_standards_reviewer_template(create_coding_standards_reviewer_agent_tools(_adapter)),
            generate_coder_template(
                create_coder_agent_tools(_adapter, platform_tools=['Write(.respec-ai/plans/*/phases/*.md)'])
            ),
        ]

        for template in templates:
            _assert_no_soft_action_language(template, _REVIEW_ACTION_SECTION_TOKENS)
