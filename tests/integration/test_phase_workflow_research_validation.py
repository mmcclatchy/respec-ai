from src.models.phase import Phase


class TestPhaseResearchValidation:
    """Test section-aware research path validation in phase-critic.

    Verifies that the phase-critic correctly distinguishes between:
    - "Existing Documentation" (should validate paths)
    - "External Research Needed" (should NOT validate paths)
    """

    def test_existing_documentation_only(self) -> None:
        research_requirements = """**Existing Documentation**:
- Read: ~/.claude/best-practices/react-hooks-2025.md
- Read: ~/.claude/best-practices/postgresql-optimization.md

No external research needed."""

        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements,
        )

        markdown = phase.build_markdown()

        assert '**Existing Documentation**:' in markdown
        assert 'Read: ~/.claude/best-practices/react-hooks-2025.md' in markdown
        assert 'Read: ~/.claude/best-practices/postgresql-optimization.md' in markdown

    def test_external_research_only(self) -> None:
        research_requirements = """**External Research Needed**:
- Synthesize: WebSocket patterns in 2025
- Synthesize: PostgreSQL optimization for microservices in 2025

No existing documentation needed."""

        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements,
        )

        markdown = phase.build_markdown()

        assert '**External Research Needed**:' in markdown
        assert 'Synthesize: WebSocket patterns in 2025' in markdown
        assert 'Synthesize: PostgreSQL optimization for microservices in 2025' in markdown

    def test_mixed_sections(self) -> None:
        research_requirements = """**Existing Documentation**:
- Read: ~/.claude/best-practices/react-hooks-2025.md

**External Research Needed**:
- Synthesize: PostgreSQL optimization in 2025"""

        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements,
        )

        markdown = phase.build_markdown()

        assert '**Existing Documentation**:' in markdown
        assert 'Read: ~/.claude/best-practices/react-hooks-2025.md' in markdown
        assert '**External Research Needed**:' in markdown
        assert 'Synthesize: PostgreSQL optimization in 2025' in markdown

    def test_invalid_read_path_should_be_flagged(self) -> None:
        research_requirements = """**Existing Documentation**:
- Read: ~/.claude/best-practices/react-hooks-2025.md
- Read: ~/.claude/best-practices/invalid-path.md

**External Research Needed**:
- Synthesize: WebSocket patterns in 2025"""

        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements,
        )

        markdown = phase.build_markdown()

        assert 'invalid-path.md' in markdown

    def test_backtick_and_plain_format_handling(self) -> None:
        research_requirements_backticks = """**Existing Documentation**:
- Read: `~/.claude/best-practices/react-hooks-2025.md`"""

        research_requirements_plain = """**Existing Documentation**:
- Read: ~/.claude/best-practices/react-hooks-2025.md"""

        phase_backticks = Phase(
            phase_name='test-phase-backticks',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements_backticks,
        )

        phase_plain = Phase(
            phase_name='test-phase-plain',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements_plain,
        )

        markdown_backticks = phase_backticks.build_markdown()
        markdown_plain = phase_plain.build_markdown()

        assert 'react-hooks-2025.md' in markdown_backticks
        assert 'react-hooks-2025.md' in markdown_plain

    def test_empty_existing_documentation_section(self) -> None:
        research_requirements = """**Existing Documentation**:
(None)

**External Research Needed**:
- Synthesize: WebSocket patterns in 2025"""

        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            research_requirements=research_requirements,
        )

        markdown = phase.build_markdown()

        assert '**Existing Documentation**:' in markdown
        assert '**External Research Needed**:' in markdown

    def test_no_research_requirements_section(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
        )

        markdown = phase.build_markdown()

        assert 'Research Requirements' not in markdown
