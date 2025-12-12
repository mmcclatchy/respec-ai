import pytest

from src.models.enums import PhaseStatus
from src.models.phase import Phase


@pytest.fixture
def markdownit_native_phase_markdown() -> str:
    return """# Phase: user-authentication-system
<!-- ID: abc12345 -->

## Overview

### Objectives
Implement secure user login and registration

### Scope
Login, logout, password reset functionality

### Dependencies
Database, encryption library

### Deliverables
Working authentication system

## System Design

### Architecture
Microservices architecture with API gateway

### Technology Stack
Python FastAPI, PostgreSQL, JWT

## Implementation

### Functional Requirements
User registration, login, logout, password reset

### Non-Functional Requirements
Response time < 200ms, 99.9% uptime

### Development Plan
Phase 1: Backend, Phase 2: Frontend integration

### Testing Strategy
Unit tests, integration tests, security testing

## Additional Details

### Research Requirements
OAuth integration patterns, JWT best practices

### Success Criteria
100% test coverage, security audit passed

### Integration Context
Connects to user service, notification service

## Metadata

### Status
in-development"""


class TestMarkdownItNativeParsing:
    def test_parse_markdownit_native_format_extracts_all_fields(self, markdownit_native_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(markdownit_native_phase_markdown)

        assert phase.phase_name == 'user-authentication-system'
        assert phase.objectives == 'Implement secure user login and registration'
        assert phase.scope == 'Login, logout, password reset functionality'
        assert phase.dependencies == 'Database, encryption library'
        assert phase.deliverables == 'Working authentication system'
        assert phase.architecture == 'Microservices architecture with API gateway'
        assert phase.technology_stack == 'Python FastAPI, PostgreSQL, JWT'
        assert phase.functional_requirements == 'User registration, login, logout, password reset'
        assert phase.non_functional_requirements == 'Response time < 200ms, 99.9% uptime'
        assert phase.development_plan == 'Phase 1: Backend, Phase 2: Frontend integration'
        assert phase.testing_strategy == 'Unit tests, integration tests, security testing'
        assert phase.research_requirements == 'OAuth integration patterns, JWT best practices'
        assert phase.success_criteria == '100% test coverage, security audit passed'
        assert phase.integration_context == 'Connects to user service, notification service'
        assert phase.phase_status == PhaseStatus.IN_DEVELOPMENT

    def test_build_markdown_creates_markdownit_native_format(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
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

        # Should use new list format
        assert '# Phase: test-phase' in markdown
        assert '## Overview' in markdown
        assert '### Objectives\nTest objectives' in markdown
        assert '### Scope\nTest scope' in markdown
        assert '### Dependencies\nTest dependencies' in markdown
        assert '### Deliverables\nTest deliverables' in markdown
        assert '## System Design' in markdown
        assert '### Architecture\nTest architecture' in markdown
        assert '### Technology Stack\nPython, FastAPI' in markdown
        assert '## Implementation' in markdown
        assert '### Functional Requirements\nLogin functionality' in markdown
        assert '### Non-Functional Requirements\nHigh performance' in markdown
        assert '### Development Plan\n3-phase approach' in markdown
        assert '### Testing Strategy\nTDD approach' in markdown
        assert '## Additional Details' in markdown
        assert '### Research Requirements\nSecurity patterns' in markdown
        assert '### Success Criteria\nAll tests pass' in markdown
        assert '### Integration Context\nAPI integration' in markdown
        assert '## Metadata' in markdown
        assert '### Status\napproved' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, markdownit_native_phase_markdown: str) -> None:
        original_phase = Phase.parse_markdown(markdownit_native_phase_markdown)

        rebuilt_markdown = original_phase.build_markdown()

        reparsed_phase = Phase.parse_markdown(rebuilt_markdown)

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


class TestRecursiveTraversalUtilities:
    def test_find_nodes_by_type_utility_exists(self) -> None:
        # This will fail until we implement the utility
        assert hasattr(Phase, '_find_nodes_by_type')

    def test_extract_text_content_utility_exists(self) -> None:
        # This will fail until we implement the utility
        assert hasattr(Phase, '_extract_text_content')
