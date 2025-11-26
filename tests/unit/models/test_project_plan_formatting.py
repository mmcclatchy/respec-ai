"""Format preservation tests for ProjectPlan model.

These tests verify that complex markdown formatting (bullet lists, code blocks,
nested lists, etc.) is preserved through parse → build → parse cycles.
"""

import pytest

from services.models.project_plan import ProjectPlan


@pytest.fixture
def project_plan_with_bullet_lists() -> str:
    return """# Project Plan: Customer Portal Redesign

## Executive Summary

### Vision
Transform customer experience through modern portal design

### Mission
Deliver user-friendly portal that improves satisfaction

### Timeline
8 months from kickoff to production

### Budget
$400,000 total project cost

## Business Objectives

### Primary Objectives
- Improve customer satisfaction scores by 30%
- Reduce support tickets by 25%
- Increase portal usage by 50%
- Enhance user engagement metrics

### Success Metrics
- Customer satisfaction score >4.5/5
- Support ticket reduction >25%
- User engagement increase >50%
- Mobile usage increase >40%

### Key Performance Indicators
- Daily active users
- Session duration
- Task completion rates
- Customer feedback scores
- Mobile vs desktop usage

## Project Scope

### Included Features
- User dashboard redesign
- Mobile responsive design
- Self-service features
- Account management tools
- Notification system

### Excluded Features
- Legacy system migration
- Third-party integrations
- Advanced analytics dashboard
- Custom reporting tools

### Assumptions
- Existing infrastructure can support new portal
- Customers will adopt new design
- No major security changes needed
- Current team has required skills

### Constraints
- Must maintain 99.9% uptime during migration
- Limited to current technology stack
- Budget cap at $400k
- 8-month timeline is fixed

## Stakeholders

### Project Sponsor
Chief Technology Officer - Sarah Johnson, provides strategic direction

### Key Stakeholders
- Customer Success team
- IT Operations
- Security team
- Executive leadership
- Customer Advisory Board

### End Users
- 5000+ active customers
- Customer support representatives
- Account managers
- System administrators

## Project Structure

### Work Breakdown
- Phase 1: Research & Design (2 months)
- Phase 2: Development (4 months)
- Phase 3: Testing & Launch (2 months)

### Phases Overview
Sequential implementation phases:
- Discovery and user research
- UI/UX design and prototyping
- Frontend development
- Backend API updates
- Testing and validation
- Deployment and rollout

### Dependencies
- Design system completion
- API documentation updates
- Security review approval
- Infrastructure scaling ready

## Resource Requirements

### Team Structure
- 1 Project Manager
- 2 Frontend Developers
- 1 Backend Developer
- 1 UI/UX Designer
- 1 QA Engineer

### Technology Requirements
- React.js frontend framework
- Node.js backend services
- PostgreSQL database
- AWS cloud infrastructure
- Docker containers

### Infrastructure Needs
- Additional AWS instances
- CDN setup for global access
- Staging environment
- Monitoring tools
- Backup systems

## Risk Management

### Identified Risks
- Timeline delays due to design complexity
- Integration challenges with legacy systems
- User adoption resistance
- Technical debt in existing code
- Resource availability issues

### Mitigation Strategies
- Regular design reviews with stakeholders
- Early integration testing
- Comprehensive user training program
- Phased rollout approach
- Cross-training team members

### Contingency Plans
- Simplified design fallback option
- Manual processes for critical features
- Extended support period post-launch
- Budget reserve for unexpected issues

## Quality Assurance

### Quality Standards
- WCAG 2.1 AA accessibility compliance
- Mobile-first responsive design
- 99.9% uptime requirement
- Sub-2 second page load times

### Testing Strategy
- Unit testing (90% coverage)
- Integration testing
- User acceptance testing
- Performance testing
- Security testing

### Acceptance Criteria
Project completion criteria:
- All features functional
- Performance benchmarks met
- Security audit passed
- User acceptance tests passed

## Communication Plan

### Reporting Structure
Weekly status reports to stakeholders

### Meeting Schedule
Regular team and stakeholder meetings

### Documentation Standards
Comprehensive project documentation

## Metadata

### Status
active
"""


@pytest.fixture
def project_plan_with_mixed_content() -> str:
    return """# Project Plan: API Platform Development

## Executive Summary

### Vision
Build a world-class API platform that enables developers to integrate seamlessly.

The platform will support both REST and GraphQL protocols.

### Mission
Deliver developer-friendly tools and documentation

### Timeline
12 months for full platform launch

### Budget
$500,000 allocated budget

## Business Objectives

### Primary Objectives
The primary goals for this project include:
- Increase API adoption by 200%
- Reduce integration time by 50%
- Achieve 99.99% uptime

We expect to reach these goals within 6 months of launch.

### Success Metrics
Key success indicators

### Key Performance Indicators
Tracking metrics

## Project Scope

### Included Features
Core platform capabilities:
- RESTful API endpoints
- GraphQL interface
- Developer documentation portal
- API key management system

Additional features will be considered for future phases.

### Excluded Features
Out of scope items

### Assumptions
Project assumptions and dependencies

### Constraints
Budget and timeline constraints

## Stakeholders

### Project Sponsor
VP of Engineering

### Key Stakeholders
Engineering and product teams

### End Users
External developers

## Project Structure

### Work Breakdown
Phased implementation

### Phases Overview
Development phases

### Dependencies
Technical dependencies

## Resource Requirements

### Team Structure
Development team composition

### Technology Requirements
Tech stack

### Infrastructure Needs
Cloud infrastructure

## Risk Management

### Identified Risks
Potential project risks

### Mitigation Strategies
Risk mitigation approach

### Contingency Plans
Backup plans

## Quality Assurance

### Quality Standards
Quality requirements

### Testing Strategy
Testing approach

### Acceptance Criteria
Completion criteria

## Metadata

### Status
draft
"""


def test_bullet_list_content_preserved_in_objectives(project_plan_with_bullet_lists: str) -> None:
    original_markdown = project_plan_with_bullet_lists

    plan = ProjectPlan.parse_markdown(original_markdown)

    assert 'Improve customer satisfaction scores by 30%' in plan.primary_objectives
    assert 'Reduce support tickets by 25%' in plan.primary_objectives
    assert 'Increase portal usage by 50%' in plan.primary_objectives

    rebuilt_markdown = plan.build_markdown()
    reparsed_plan = ProjectPlan.parse_markdown(rebuilt_markdown)

    assert plan.primary_objectives == reparsed_plan.primary_objectives, (
        'Primary Objectives content changed during round-trip'
    )


def test_bullet_list_content_preserved_in_success_metrics(project_plan_with_bullet_lists: str) -> None:
    original_markdown = project_plan_with_bullet_lists

    plan = ProjectPlan.parse_markdown(original_markdown)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert 'Customer satisfaction score >4.5/5' in plan.success_metrics
    assert 'Support ticket reduction >25%' in plan.success_metrics
    assert 'User engagement increase >50%' in plan.success_metrics

    assert plan.success_metrics == reparsed.success_metrics, 'Success Metrics content changed during round-trip'


def test_bullet_list_content_preserved_in_included_features(project_plan_with_bullet_lists: str) -> None:
    original_markdown = project_plan_with_bullet_lists

    plan = ProjectPlan.parse_markdown(original_markdown)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert 'User dashboard redesign' in plan.included_features
    assert 'Mobile responsive design' in plan.included_features
    assert 'Self-service features' in plan.included_features

    assert plan.included_features == reparsed.included_features, 'Included Features content changed during round-trip'


def test_mixed_content_format_preserved(project_plan_with_mixed_content: str) -> None:
    original_markdown = project_plan_with_mixed_content

    plan = ProjectPlan.parse_markdown(original_markdown)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert 'world-class API platform' in plan.project_vision
    assert 'REST and GraphQL protocols' in plan.project_vision

    assert 'Increase API adoption by 200%' in plan.primary_objectives
    assert 'Reduce integration time by 50%' in plan.primary_objectives
    assert (
        'reach these goals within 6 months' in plan.primary_objectives or 'expect to reach' in plan.primary_objectives
    )

    assert plan.project_vision == reparsed.project_vision, 'Vision content changed during round-trip'
    assert plan.primary_objectives == reparsed.primary_objectives, (
        'Primary Objectives content changed during round-trip'
    )


def test_plain_text_content_still_works() -> None:
    markdown = """# Project Plan: Simple Project

## Executive Summary

### Vision
Simple vision statement

### Mission
Simple mission

### Timeline
6 months

### Budget
$100,000

## Business Objectives

### Primary Objectives
Deliver on time

### Success Metrics
Project completed

### Key Performance Indicators
On-time delivery

## Metadata

### Status
active
"""

    plan = ProjectPlan.parse_markdown(markdown)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert plan.primary_objectives == 'Deliver on time'
    assert plan.primary_objectives == reparsed.primary_objectives


def test_character_for_character_round_trip(project_plan_with_bullet_lists: str) -> None:
    original_markdown = project_plan_with_bullet_lists

    first_parse = ProjectPlan.parse_markdown(original_markdown)
    first_build = first_parse.build_markdown()
    second_parse = ProjectPlan.parse_markdown(first_build)
    second_build = second_parse.build_markdown()

    assert first_build == second_build, 'Markdown changed between first and second round-trip'


def test_ordered_lists_preserved() -> None:
    markdown_with_ordered_lists = """# Project Plan: Phased Implementation

## Executive Summary

### Vision
Systematic rollout approach

### Mission
Deliver in phases

### Timeline
12 months

### Budget
$600,000

## Business Objectives

### Primary Objectives
1. Phase 1: Complete foundation by month 3
2. Phase 2: Deliver core features by month 6
3. Phase 3: Launch full platform by month 12

### Success Metrics
1. Foundation milestone achieved
2. Core features validated
3. Platform fully operational

### Key Performance Indicators
Milestone completion tracking

## Project Scope

### Included Features
1. First feature: User authentication system
2. Second feature: Data processing pipeline
3. Third feature: Reporting dashboard
4. Fourth feature: Admin panel

### Excluded Features
Out of scope items

### Assumptions
Project assumptions

### Constraints
Project constraints

## Metadata

### Status
draft
"""

    plan = ProjectPlan.parse_markdown(markdown_with_ordered_lists)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert 'Phase 1: Complete foundation' in plan.primary_objectives
    assert 'Phase 2: Deliver core features' in plan.primary_objectives
    assert 'Phase 3: Launch full platform' in plan.primary_objectives

    assert 'First feature: User authentication' in plan.included_features
    assert 'Second feature: Data processing' in plan.included_features

    assert plan.primary_objectives == reparsed.primary_objectives, 'Ordered list content changed during round-trip'
    assert plan.included_features == reparsed.included_features, 'Features list changed during round-trip'


def test_nested_bullet_lists_preserved() -> None:
    markdown_with_nested_lists = """# Project Plan: Complex Structure

## Executive Summary

### Vision
Multi-tier project organization

### Mission
Deliver structured solution

### Timeline
18 months

### Budget
$800,000

## Business Objectives

### Primary Objectives
- Strategic Objective A: Market Expansion
  - Sub-goal A1: Enter EMEA market
  - Sub-goal A2: Establish APAC presence
    - Detail: Research market requirements
    - Detail: Hire local teams
- Strategic Objective B: Product Innovation
  - Sub-goal B1: Launch new features
  - Sub-goal B2: Improve existing products

### Success Metrics
Key metrics for tracking

### Key Performance Indicators
Performance tracking

## Project Scope

### Included Features
- Feature Category 1: Core Platform
  - Component: Authentication system
  - Component: User management
- Feature Category 2: Advanced Features
  - Component: Analytics dashboard
  - Component: Reporting tools

### Excluded Features
Out of scope

### Assumptions
Assumptions

### Constraints
Constraints

## Metadata

### Status
draft
"""

    plan = ProjectPlan.parse_markdown(markdown_with_nested_lists)
    rebuilt = plan.build_markdown()
    reparsed = ProjectPlan.parse_markdown(rebuilt)

    assert 'Strategic Objective A: Market Expansion' in plan.primary_objectives
    assert 'Sub-goal A1: Enter EMEA market' in plan.primary_objectives
    assert (
        'Detail: Research market requirements' in plan.primary_objectives
        or 'Research market requirements' in plan.primary_objectives
    )

    assert 'Feature Category 1: Core Platform' in plan.included_features
    assert 'Component: Authentication system' in plan.included_features

    assert plan.primary_objectives == reparsed.primary_objectives, 'Nested objectives changed during round-trip'
    assert plan.included_features == reparsed.included_features, 'Nested features changed during round-trip'
