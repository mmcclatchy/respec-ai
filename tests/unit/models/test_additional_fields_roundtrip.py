from src.models.feature_requirements import FeatureRequirements
from src.models.phase import Phase
from src.models.roadmap import Roadmap
from src.models.task import Task


class TestTaskResearchRoundTrip:
    def test_research_field_parsed_from_markdown(self) -> None:
        markdown = """# Task: task-1-auth

## Identity

### Phase Path
test/phase-1

## Overview

### Goal
Implement login

### Acceptance Criteria
Users can login

### Technology Stack Reference
FastAPI

## Implementation

### Checklist
- [ ] Setup OAuth2

### Steps
#### Step 1: Setup
Install packages

## Quality

### Testing Strategy
Unit tests

## Research

### Research Read Log
Documents successfully read:
- `.best-practices/jwt-best-practices.md` - Applied: token expiry patterns

Documents referenced but unavailable:
- None

## Status

### Current Status
pending

## Metadata

### Active
true

### Version
1.0
"""
        task = Task.parse_markdown(markdown)

        assert 'jwt-best-practices.md' in task.research
        assert 'token expiry patterns' in task.research

    def test_research_field_round_trip(self) -> None:
        task = Task(
            name='task-1-auth',
            phase_path='test/phase-1',
            research='Documents successfully read:\n- `.best-practices/jwt.md` - Applied: token patterns',
        )
        markdown = task.build_markdown()
        parsed = Task.parse_markdown(markdown)

        assert parsed.research == task.research

    def test_research_default_when_missing(self) -> None:
        markdown = """# Task: task-1-auth

## Identity

### Phase Path
test/phase-1

## Overview

### Goal
Implement login

### Acceptance Criteria
Users can login

### Technology Stack Reference
FastAPI

## Implementation

### Checklist
- [ ] Setup

### Steps
#### Step 1: Setup
Install

## Quality

### Testing Strategy
Unit tests

## Status

### Current Status
pending

## Metadata

### Active
true

### Version
1.0
"""
        task = Task.parse_markdown(markdown)
        assert task.research == 'Research not specified'


class TestTaskAdditionalSections:
    def test_additional_sections_captured_from_markdown(self) -> None:
        markdown = """# Task: task-1-auth

## Identity

### Phase Path
test/phase-1

## Overview

### Goal
Implement login

### Acceptance Criteria
Users can login

### Technology Stack Reference
FastAPI

## Implementation

### Checklist
- [ ] Setup

### Steps
#### Step 1: Setup
Install

## Quality

### Testing Strategy
Unit tests

## Research

### Research Read Log
No research provided

## Custom Notes

Agent-specific notes about this task

## Status

### Current Status
pending

## Metadata

### Active
true

### Version
1.0
"""
        task = Task.parse_markdown(markdown)

        assert task.additional_sections is not None
        assert 'Custom Notes' in task.additional_sections
        assert 'Agent-specific notes' in task.additional_sections['Custom Notes']

    def test_additional_sections_round_trip(self) -> None:
        task = Task(
            name='task-1-auth',
            phase_path='test/phase-1',
            additional_sections={
                'Custom Notes': 'Agent-specific notes',
                'References': 'External documentation links',
            },
        )
        markdown = task.build_markdown()
        parsed = Task.parse_markdown(markdown)

        assert parsed.additional_sections is not None
        assert 'Custom Notes' in parsed.additional_sections
        assert 'References' in parsed.additional_sections


class TestRoadmapAdditionalSections:
    def test_additional_sections_captured_from_markdown(self) -> None:
        markdown = """# Plan Roadmap: Test Project

## Plan Details

### Plan Goal
Build platform

### Total Duration
6 months

### Team Size
4 developers

### Budget
$100K

## Risk Assessment

### Critical Path Analysis
Sequential phases

### Key Risks
Technical complexity

### Mitigation Plans
Incremental delivery

### Buffer Time
2 weeks

## Resource Planning

### Development Resources
4 developers

### Infrastructure Requirements
Cloud hosting

### External Dependencies
None

### Quality Assurance Plan
Automated testing

## Success Metrics

### Technical Milestones
MVP delivery

### Business Milestones
User acceptance

### Quality Gates
All tests pass

### Performance Targets
Sub-2s response

## Custom Analysis

Competitive landscape analysis and market research notes

## Metadata

### Status
draft

### Phase Count
0
"""
        roadmap = Roadmap.parse_markdown(markdown)

        assert roadmap.additional_sections is not None
        assert 'Custom Analysis' in roadmap.additional_sections
        assert 'Competitive landscape' in roadmap.additional_sections['Custom Analysis']

    def test_additional_sections_round_trip(self) -> None:
        roadmap = Roadmap(
            plan_name='Test Project',
            additional_sections={
                'Custom Analysis': 'Market research notes',
            },
        )
        markdown = roadmap.build_markdown()
        parsed = Roadmap.parse_markdown(markdown)

        assert parsed.additional_sections is not None
        assert 'Custom Analysis' in parsed.additional_sections
        assert 'Market research notes' in parsed.additional_sections['Custom Analysis']


class TestFeatureRequirementsAdditionalSections:
    def test_additional_sections_round_trip(self) -> None:
        reqs = FeatureRequirements(
            plan_name='Auth Feature',
            additional_sections={
                'Compliance Notes': 'GDPR requirements for auth data',
            },
        )
        markdown = reqs.build_markdown()
        parsed = FeatureRequirements.parse_markdown(markdown)

        assert parsed.additional_sections is not None
        assert 'Compliance Notes' in parsed.additional_sections
        assert 'GDPR requirements' in parsed.additional_sections['Compliance Notes']


class TestPhasePerH2AdditionalSections:
    def test_system_design_additional_parsed_from_markdown(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Build the thing

### Scope
Everything

### Dependencies
None

### Deliverables
Working service

## System Design

### Architecture
Microservice architecture

### Technology Stack
Python FastAPI

### System Design - Additional Sections
#### Notion Data Model
11 kanban columns, 18 job card fields

#### Cost Monitoring
Monthly budget alerts via DigitalOcean

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""
        phase = Phase.parse_markdown(markdown)

        assert phase.system_design_additional is not None
        assert 'Notion Data Model' in phase.system_design_additional
        assert '11 kanban columns' in phase.system_design_additional
        assert 'Cost Monitoring' in phase.system_design_additional

    def test_system_design_additional_round_trip(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            architecture='Microservice architecture',
            technology_stack='Python FastAPI',
            system_design_additional='#### Notion Data Model\n11 kanban columns\n\n#### Cost Monitoring\nMonthly alerts',
        )
        markdown = phase.build_markdown()
        parsed = Phase.parse_markdown(markdown)

        assert parsed.system_design_additional == phase.system_design_additional

    def test_implementation_additional_round_trip(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            functional_requirements='Core features',
            testing_strategy='Unit tests',
            implementation_additional='#### Custom Workflow\nSpecial CI/CD pipeline configuration',
        )
        markdown = phase.build_markdown()
        parsed = Phase.parse_markdown(markdown)

        assert parsed.implementation_additional == phase.implementation_additional

    def test_additional_details_additional_round_trip(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            research_requirements='JWT best practices',
            success_criteria='All tests pass',
            additional_details_additional='#### Compliance Notes\nGDPR requirements',
        )
        markdown = phase.build_markdown()
        parsed = Phase.parse_markdown(markdown)

        assert parsed.additional_details_additional == phase.additional_details_additional

    def test_per_h2_additional_coexists_with_h2_additional_sections(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            architecture='Microservices',
            system_design_additional='#### Custom Data Model\nER diagrams',
            additional_sections={
                'Data Models': 'Full schema definitions',
                'API Design': 'REST endpoint specifications',
            },
        )
        markdown = phase.build_markdown()
        parsed = Phase.parse_markdown(markdown)

        assert parsed.system_design_additional == phase.system_design_additional
        assert parsed.additional_sections is not None
        assert 'Data Models' in parsed.additional_sections
        assert 'API Design' in parsed.additional_sections

    def test_none_when_no_additional_content(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            architecture='Microservices',
        )
        assert phase.system_design_additional is None
        assert phase.implementation_additional is None
        assert phase.additional_details_additional is None

        markdown = phase.build_markdown()
        assert '### System Design - Additional Sections' not in markdown
        assert '### Implementation - Additional Sections' not in markdown
