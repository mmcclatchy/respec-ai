import pytest

from services.models.enums import SpecStatus
from services.models.spec import TechnicalSpec


@pytest.fixture
def complete_spec_markdown() -> str:
    return """# Technical Specification: test-phase

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
def minimal_spec_markdown() -> str:
    return """# Technical Specification: minimal-spec

## Overview

### Objectives
Basic functionality
"""


@pytest.fixture
def round_trip_spec_markdown() -> str:
    return """# Technical Specification: round-trip-test

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


class TestTechnicalSpecParsing:
    def test_parse_markdown_extracts_all_fields(self, complete_spec_markdown: str) -> None:
        spec = TechnicalSpec.parse_markdown(complete_spec_markdown)

        assert spec.phase_name == 'test-phase'
        assert spec.objectives == 'Implement user authentication system'
        assert spec.scope == 'Login, logout, password reset functionality'
        assert spec.dependencies == 'User database, JWT library'
        assert spec.deliverables == 'Authentication service, login UI, password reset flow'
        assert spec.architecture == 'Microservice architecture with JWT tokens'
        assert spec.technology_stack == 'Python FastAPI, PostgreSQL, JWT'
        assert spec.functional_requirements == 'User login with email/password, secure password storage'
        assert spec.non_functional_requirements == 'Response time < 200ms, 99.9% uptime'
        assert spec.development_plan == 'Phase 1: Backend service, Phase 2: Frontend integration'
        assert spec.testing_strategy == 'Unit tests, integration tests, security testing'
        assert spec.research_requirements == 'OAuth integration patterns, JWT best practices'
        assert spec.success_criteria == '100% test coverage, security audit passed'
        assert spec.integration_context == 'Connects to user service, notification service'
        assert spec.spec_status == SpecStatus.IN_DEVELOPMENT

    def test_parse_markdown_handles_missing_sections(self, minimal_spec_markdown: str) -> None:
        spec = TechnicalSpec.parse_markdown(minimal_spec_markdown)

        assert spec.phase_name == 'minimal-spec'
        assert spec.objectives == 'Basic functionality'
        assert spec.scope != ''
        assert spec.technology_stack != ''

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = 'This is not a valid specification'

        with pytest.raises(ValueError, match='Invalid technical spec format'):
            TechnicalSpec.parse_markdown(invalid_markdown)


class TestTechnicalSpecMarkdownBuilding:
    def test_build_markdown_creates_valid_template_format(self) -> None:
        spec = TechnicalSpec(
            phase_name='test-spec',
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
            spec_status=SpecStatus.APPROVED,
        )

        markdown = spec.build_markdown()

        assert '# Technical Specification: test-spec' in markdown
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

    def test_round_trip_parsing_maintains_data_integrity(self, round_trip_spec_markdown: str) -> None:
        spec = TechnicalSpec.parse_markdown(round_trip_spec_markdown)

        rebuilt_markdown = spec.build_markdown()

        parsed_spec = TechnicalSpec.parse_markdown(rebuilt_markdown)

        assert spec.phase_name == parsed_spec.phase_name
        assert spec.objectives == parsed_spec.objectives
        assert spec.scope == parsed_spec.scope
        assert spec.dependencies == parsed_spec.dependencies
        assert spec.deliverables == parsed_spec.deliverables
        assert spec.architecture == parsed_spec.architecture
        assert spec.research_requirements == parsed_spec.research_requirements
        assert spec.success_criteria == parsed_spec.success_criteria
        assert spec.integration_context == parsed_spec.integration_context

    def test_round_trip_data_integrity_validation(self, round_trip_spec_markdown: str) -> None:
        original_spec = TechnicalSpec.parse_markdown(round_trip_spec_markdown)

        rebuilt_markdown = original_spec.build_markdown()

        reparsed_spec = TechnicalSpec.parse_markdown(rebuilt_markdown)

        # Verify data integrity is preserved through round-trip
        assert original_spec.phase_name == reparsed_spec.phase_name
        assert original_spec.objectives == reparsed_spec.objectives
        assert original_spec.scope == reparsed_spec.scope
        assert original_spec.dependencies == reparsed_spec.dependencies
        assert original_spec.deliverables == reparsed_spec.deliverables
        assert original_spec.architecture == reparsed_spec.architecture
        assert original_spec.technology_stack == reparsed_spec.technology_stack
        assert original_spec.functional_requirements == reparsed_spec.functional_requirements
        assert original_spec.non_functional_requirements == reparsed_spec.non_functional_requirements
        assert original_spec.development_plan == reparsed_spec.development_plan
        assert original_spec.testing_strategy == reparsed_spec.testing_strategy
        assert original_spec.research_requirements == reparsed_spec.research_requirements
        assert original_spec.success_criteria == reparsed_spec.success_criteria
        assert original_spec.integration_context == reparsed_spec.integration_context
        assert original_spec.spec_status == reparsed_spec.spec_status
