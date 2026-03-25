import pytest

from src.models.enums import PhaseStatus
from src.models.phase import Phase


@pytest.fixture
def complete_phase_markdown() -> str:
    return """# Phase: test-phase

## Overview

### Objectives
Implement user authentication system

### Scope
Login, logout, password reset functionality

### Dependencies
User database, JWT library

### Deliverables
Authentication service, login UI, password reset flow

## System Design

### Architecture
Microservice architecture with JWT tokens

### Technology Stack
Python FastAPI, PostgreSQL, JWT

## Implementation

### Functional Requirements
User login with email/password, secure password storage

### Non-Functional Requirements
Response time < 200ms, 99.9% uptime

### Development Plan
Phase 1: Backend service, Phase 2: Frontend integration

### Testing Strategy
Unit tests, integration tests, security testing

## Additional Details

### Implementation Plan References
Pre-resolved architecture decisions.

- Constraint: `~/.claude/plans/test-plan.md` § "Architecture Decision Log"

### Research Requirements
OAuth integration patterns, JWT best practices

### Success Criteria
100% test coverage, security audit passed

### Integration Context
Connects to user service, notification service

## Metadata

### Status
in-development
"""


@pytest.fixture
def minimal_phase_markdown() -> str:
    return """# Phase: minimal-phase

## Overview

### Objectives
Basic functionality
"""


@pytest.fixture
def round_trip_phase_markdown() -> str:
    return """# Phase: round-trip-test

## Overview
**Objectives**: `Test round trip parsing`
**Scope**: `Complete data preservation`
**Dependencies**: `None`

## Deliverables
`Validated parsing system`

## System Design

### Architecture
`Clean architecture pattern`

### Technology Stack
`Python 3.11, Pydantic`

## Implementation

### Functional Requirements
`Complete field mapping`

### Non-Functional Requirements
`Zero data loss`

### Development Plan
`Single iteration`

### Testing Strategy
`Round-trip validation`

## Additional Details

### Research Requirements
Parsing best practices

### Success Criteria
Character-for-character match

### Integration Context
Standalone component

## Metadata

### Status
approved
"""


class TestPhaseParsing:
    def test_parse_markdown_extracts_all_fields(self, complete_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(complete_phase_markdown)

        assert phase.phase_name == 'test-phase'
        assert phase.objectives == 'Implement user authentication system'
        assert phase.scope == 'Login, logout, password reset functionality'
        assert phase.dependencies == 'User database, JWT library'
        assert phase.deliverables == 'Authentication service, login UI, password reset flow'
        assert phase.architecture == 'Microservice architecture with JWT tokens'
        assert phase.technology_stack == 'Python FastAPI, PostgreSQL, JWT'
        assert phase.functional_requirements == 'User login with email/password, secure password storage'
        assert phase.non_functional_requirements == 'Response time < 200ms, 99.9% uptime'
        assert phase.development_plan == 'Phase 1: Backend service, Phase 2: Frontend integration'
        assert phase.testing_strategy == 'Unit tests, integration tests, security testing'
        assert phase.research_requirements == 'OAuth integration patterns, JWT best practices'
        assert phase.success_criteria == '100% test coverage, security audit passed'
        assert phase.integration_context == 'Connects to user service, notification service'
        assert phase.phase_status == PhaseStatus.IN_DEVELOPMENT
        assert phase.implementation_plan_references is not None
        assert '~/.claude/plans/test-plan.md' in phase.implementation_plan_references

    def test_parse_markdown_handles_missing_sections(self, minimal_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(minimal_phase_markdown)

        assert phase.phase_name == 'minimal-phase'
        assert phase.objectives == 'Basic functionality'
        assert phase.scope != ''
        assert phase.technology_stack != ''

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = 'This is not a valid specification'

        with pytest.raises(ValueError, match='Invalid phase format'):
            Phase.parse_markdown(invalid_markdown)


class TestPhaseMarkdownBuilding:
    def test_build_markdown_creates_valid_template_format(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test deps',
            deliverables='Test deliverables',
            architecture='Test architecture',
            technology_stack='Python, FastAPI',
            functional_requirements='Login functionality',
            non_functional_requirements='High performance',
            development_plan='3-phase approach',
            testing_strategy='TDD approach',
            research_requirements='Security patterns',
            success_criteria='All tests pass',
            integration_context='API integration',
            phase_status=PhaseStatus.APPROVED,
        )

        markdown = phase.build_markdown()

        assert '# Phase: test-phase' in markdown
        assert '### Objectives\nTest objectives' in markdown
        assert '### Scope\nTest scope' in markdown
        assert '### Dependencies\nTest deps' in markdown
        assert '### Deliverables\nTest deliverables' in markdown
        assert '### Architecture\nTest architecture' in markdown
        assert '### Technology Stack\nPython, FastAPI' in markdown
        assert '### Functional Requirements\nLogin functionality' in markdown
        assert '### Non-Functional Requirements\nHigh performance' in markdown
        assert '### Development Plan\n3-phase approach' in markdown
        assert '### Testing Strategy\nTDD approach' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, round_trip_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(round_trip_phase_markdown)

        rebuilt_markdown = phase.build_markdown()

        parsed_phase = Phase.parse_markdown(rebuilt_markdown)

        assert phase.phase_name == parsed_phase.phase_name
        assert phase.objectives == parsed_phase.objectives
        assert phase.scope == parsed_phase.scope
        assert phase.dependencies == parsed_phase.dependencies
        assert phase.deliverables == parsed_phase.deliverables
        assert phase.architecture == parsed_phase.architecture
        assert phase.research_requirements == parsed_phase.research_requirements
        assert phase.success_criteria == parsed_phase.success_criteria
        assert phase.integration_context == parsed_phase.integration_context

    def test_round_trip_data_integrity_validation(self, round_trip_phase_markdown: str) -> None:
        original_phase = Phase.parse_markdown(round_trip_phase_markdown)

        rebuilt_markdown = original_phase.build_markdown()

        reparsed_phase = Phase.parse_markdown(rebuilt_markdown)

        # Verify data integrity is preserved through round-trip
        assert original_phase.phase_name == reparsed_phase.phase_name
        assert original_phase.objectives == reparsed_phase.objectives
        assert original_phase.scope == reparsed_phase.scope
        assert original_phase.dependencies == reparsed_phase.dependencies
        assert original_phase.deliverables == reparsed_phase.deliverables
        assert original_phase.architecture == reparsed_phase.architecture
        assert original_phase.technology_stack == reparsed_phase.technology_stack
        assert original_phase.functional_requirements == reparsed_phase.functional_requirements
        assert original_phase.non_functional_requirements == reparsed_phase.non_functional_requirements
        assert original_phase.development_plan == reparsed_phase.development_plan
        assert original_phase.testing_strategy == reparsed_phase.testing_strategy
        assert original_phase.research_requirements == reparsed_phase.research_requirements
        assert original_phase.success_criteria == reparsed_phase.success_criteria
        assert original_phase.integration_context == reparsed_phase.integration_context
        assert original_phase.phase_status == reparsed_phase.phase_status

    def test_parse_markdown_extracts_implementation_plan_references(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Test objectives

## Additional Details

### Implementation Plan References
Pre-resolved architecture decisions.

- Constraint: `~/.claude/plans/my-plan.md` § "Technology Decisions"
  (fpdf2 chosen over WeasyPrint due to DigitalOcean Functions constraints)
"""
        phase = Phase.parse_markdown(markdown)

        assert phase.implementation_plan_references is not None
        assert '~/.claude/plans/my-plan.md' in phase.implementation_plan_references
        assert 'Technology Decisions' in phase.implementation_plan_references

    def test_build_markdown_includes_implementation_plan_references(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            implementation_plan_references='- Constraint: `~/.claude/plans/test.md`',
        )

        markdown = phase.build_markdown()

        assert '### Implementation Plan References' in markdown
        assert '~/.claude/plans/test.md' in markdown
        impl_pos = markdown.index('### Implementation Plan References')
        research_pos = (
            markdown.index('### Research Requirements') if '### Research Requirements' in markdown else len(markdown)
        )
        assert impl_pos < research_pos

    def test_build_markdown_omits_implementation_plan_references_when_none(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
        )

        markdown = phase.build_markdown()

        assert '### Implementation Plan References' not in markdown

    def test_round_trip_with_implementation_plan_references(self, complete_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(complete_phase_markdown)

        rebuilt = phase.build_markdown()

        reparsed = Phase.parse_markdown(rebuilt)

        assert reparsed.implementation_plan_references == phase.implementation_plan_references
        assert reparsed.research_requirements == phase.research_requirements
