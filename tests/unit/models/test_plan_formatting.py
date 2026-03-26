import pytest

from src.models.plan import Plan


@pytest.fixture
def plan_with_bullet_lists() -> str:
    return """# Plan Plan: Customer Portal Redesign

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

## Plan Scope

### Included Features
- User dashboard redesign
- Mobile responsive design
- Self-service features
- Account management tools
- Notification system

### Anti-Requirements
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

### Plan Sponsor
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

## Plan Structure

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
- 1 Plan Manager
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

### Quality Bar
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

## Metadata

### Status
active
"""


@pytest.fixture
def plan_with_mixed_content() -> str:
    return """# Plan Plan: API Platform Development

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

## Plan Scope

### Included Features
Core platform capabilities:
- RESTful API endpoints
- GraphQL interface
- Developer documentation portal
- API key management system

Additional features will be considered for future phases.

### Anti-Requirements
Out of scope items

### Assumptions
Project assumptions and dependencies

### Constraints
Budget and timeline constraints

## Stakeholders

### Plan Sponsor
VP of Engineering

### Key Stakeholders
Engineering and product teams

### End Users
External developers

## Plan Structure

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

### Quality Bar
Quality requirements

### Testing Strategy
Testing approach

### Acceptance Criteria
Completion criteria

## Metadata

### Status
draft
"""


def test_bullet_list_content_preserved_in_objectives(plan_with_bullet_lists: str) -> None:
    plan = Plan.parse_markdown(plan_with_bullet_lists)

    assert 'Improve customer satisfaction scores by 30%' in plan.business_objectives
    assert 'Reduce support tickets by 25%' in plan.business_objectives
    assert 'Increase portal usage by 50%' in plan.business_objectives

    rebuilt_markdown = plan.build_markdown()
    reparsed_plan = Plan.parse_markdown(rebuilt_markdown)

    assert plan.business_objectives == reparsed_plan.business_objectives, (
        'Business Objectives content changed during round-trip'
    )


def test_bullet_list_content_preserved_in_success_metrics(plan_with_bullet_lists: str) -> None:
    plan = Plan.parse_markdown(plan_with_bullet_lists)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'Customer satisfaction score >4.5/5' in plan.business_objectives
    assert 'Support ticket reduction >25%' in plan.business_objectives

    assert plan.business_objectives == reparsed.business_objectives, (
        'Business Objectives content changed during round-trip'
    )


def test_bullet_list_content_preserved_in_included_features(plan_with_bullet_lists: str) -> None:
    plan = Plan.parse_markdown(plan_with_bullet_lists)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'User dashboard redesign' in plan.plan_scope
    assert 'Mobile responsive design' in plan.plan_scope
    assert 'Self-service features' in plan.plan_scope

    assert plan.plan_scope == reparsed.plan_scope, 'Plan Scope content changed during round-trip'


def test_mixed_content_format_preserved(plan_with_mixed_content: str) -> None:
    plan = Plan.parse_markdown(plan_with_mixed_content)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'world-class API platform' in plan.executive_summary
    assert 'REST and GraphQL protocols' in plan.executive_summary

    assert 'Increase API adoption by 200%' in plan.business_objectives
    assert 'Reduce integration time by 50%' in plan.business_objectives

    assert plan.executive_summary == reparsed.executive_summary, 'Executive Summary content changed during round-trip'
    assert plan.business_objectives == reparsed.business_objectives, (
        'Business Objectives content changed during round-trip'
    )


def test_plain_text_content_still_works() -> None:
    markdown = """# Plan Plan: Simple Plan

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

    plan = Plan.parse_markdown(markdown)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'Deliver on time' in plan.business_objectives
    assert plan.business_objectives == reparsed.business_objectives


def test_character_for_character_round_trip(plan_with_bullet_lists: str) -> None:
    first_parse = Plan.parse_markdown(plan_with_bullet_lists)
    first_build = first_parse.build_markdown()
    second_parse = Plan.parse_markdown(first_build)
    second_build = second_parse.build_markdown()

    assert first_build == second_build, 'Markdown changed between first and second round-trip'


def test_ordered_lists_preserved() -> None:
    markdown_with_ordered_lists = """# Plan Plan: Phased Implementation

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

## Plan Scope

### Included Features
1. First feature: User authentication system
2. Second feature: Data processing pipeline
3. Third feature: Reporting dashboard
4. Fourth feature: Admin panel

### Anti-Requirements
Out of scope items

### Assumptions
Project assumptions

### Constraints
Project constraints

## Metadata

### Status
draft
"""

    plan = Plan.parse_markdown(markdown_with_ordered_lists)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'Phase 1: Complete foundation' in plan.business_objectives
    assert 'Phase 2: Deliver core features' in plan.business_objectives
    assert 'Phase 3: Launch full platform' in plan.business_objectives

    assert 'First feature: User authentication' in plan.plan_scope
    assert 'Second feature: Data processing' in plan.plan_scope

    assert plan.business_objectives == reparsed.business_objectives, 'Ordered list content changed during round-trip'
    assert plan.plan_scope == reparsed.plan_scope, 'Features list changed during round-trip'


def test_nested_bullet_lists_preserved() -> None:
    markdown_with_nested_lists = """# Plan Plan: Complex Structure

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

## Plan Scope

### Included Features
- Feature Category 1: Core Platform
  - Component: Authentication system
  - Component: User management
- Feature Category 2: Advanced Features
  - Component: Analytics dashboard
  - Component: Reporting tools

### Anti-Requirements
Out of scope

### Assumptions
Assumptions

### Constraints
Constraints

## Metadata

### Status
draft
"""

    plan = Plan.parse_markdown(markdown_with_nested_lists)
    rebuilt = plan.build_markdown()
    reparsed = Plan.parse_markdown(rebuilt)

    assert 'Strategic Objective A: Market Expansion' in plan.business_objectives
    assert 'Sub-goal A1: Enter EMEA market' in plan.business_objectives
    assert (
        'Detail: Research market requirements' in plan.business_objectives
        or 'Research market requirements' in plan.business_objectives
    )

    assert 'Feature Category 1: Core Platform' in plan.plan_scope
    assert 'Component: Authentication system' in plan.plan_scope

    assert plan.business_objectives == reparsed.business_objectives, 'Nested objectives changed during round-trip'
    assert plan.plan_scope == reparsed.plan_scope, 'Nested features changed during round-trip'
