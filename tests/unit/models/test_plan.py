import pytest

from src.models.enums import PlanStatus
from src.models.plan import Plan


class TestPlanParsing:
    def test_parse_markdown_extracts_all_fields(self) -> None:
        markdown = """# Plan Plan: Customer Portal Redesign

## Executive Summary

### Vision
Transform customer experience through modern, intuitive portal design

### Mission
Deliver a user-friendly portal that increases customer satisfaction and reduces support tickets

### Timeline
8 months from project kickoff to production deployment

### Budget
$400,000 including development, design, and infrastructure costs

## Business Objectives

### Primary Objectives
Improve customer satisfaction scores by 30%, reduce support tickets by 25%, increase portal usage by 50%

### Success Metrics
Customer satisfaction score >4.5/5, support ticket reduction >25%, user engagement increase >50%

### Key Performance Indicators
Daily active users, session duration, task completion rates, customer feedback scores

## Plan Scope

### Included Features
User dashboard redesign, mobile responsive design, self-service features, account management tools

### Anti-Requirements
No legacy system migration, no third-party integrations, no advanced analytics dashboard

### Assumptions
Existing infrastructure can support new portal, customers will adopt new design, no major security changes needed

### Constraints
Must maintain 99.9% uptime during migration, limited to current technology stack, budget cap at $400k

## Stakeholders

### Plan Sponsor
Chief Technology Officer - Sarah Johnson, provides strategic direction and final approvals

### Key Stakeholders
Customer Success team, IT Operations, Security team, Executive leadership, Customer Advisory Board

### End Users
Existing customers (5000+ active users), customer support representatives, account managers

## Architecture Direction

### Architecture Overview
React SPA frontend, Node.js API backend, PostgreSQL database with Redis cache layer

### Data Flow
Client requests → API Gateway → Node.js handlers → PostgreSQL/Redis → JSON response

## Technology Decisions

### Chosen Technologies
React.js chosen for component reuse, Node.js chosen for team familiarity, PostgreSQL for ACID compliance

### Rejected Technologies
Vue.js rejected due to smaller team familiarity, MongoDB rejected due to relational data requirements

## Plan Structure

### Work Breakdown
Phase 1: Research & Design (2 months), Phase 2: Development (4 months), Phase 3: Testing & Launch (2 months)

### Phases Overview
Discovery and user research, UI/UX design, frontend development, backend API updates, testing, deployment

### Dependencies
Design system completion, API documentation updates, security review approval, infrastructure scaling

## Resource Requirements

### Team Structure
1 Plan Manager, 2 Frontend Developers, 1 Backend Developer, 1 UI/UX Designer, 1 QA Engineer

### Technology Requirements
React.js frontend, Node.js backend, PostgreSQL database, AWS cloud infrastructure, Docker containers

### Infrastructure Needs
Additional AWS instances, CDN setup, staging environment, monitoring tools, backup systems

## Risk Management

### Identified Risks
Timeline delays due to design complexity, integration challenges with legacy systems, user adoption resistance

### Mitigation Strategies
Regular design reviews, early integration testing, comprehensive user training program, phased rollout

### Contingency Plans
Simplified design fallback, manual processes for critical features, extended support period post-launch

## Quality Assurance

### Quality Bar
WCAG 2.1 AA accessibility compliance, mobile-first responsive design, 99.9% uptime requirement, 90% test coverage

### Testing Strategy
Unit testing (90% coverage), integration testing, user acceptance testing, performance testing, security testing

### Acceptance Criteria
All user stories complete, performance benchmarks met, security scan passed, stakeholder sign-off received

## Metadata

### Status
approved
"""

        plan = Plan.parse_markdown(markdown)

        assert plan.plan_name == 'Customer Portal Redesign'

        # H2 fields capture all content including H3 sub-headers
        assert 'Transform customer experience' in plan.executive_summary
        assert '### Vision' in plan.executive_summary
        assert '### Mission' in plan.executive_summary
        assert '### Timeline' in plan.executive_summary
        assert '### Budget' in plan.executive_summary

        assert 'Improve customer satisfaction scores by 30%' in plan.business_objectives
        assert '### Primary Objectives' in plan.business_objectives
        assert '### Success Metrics' in plan.business_objectives

        assert 'User dashboard redesign' in plan.plan_scope
        assert 'No legacy system migration' in plan.plan_scope

        assert 'Chief Technology Officer - Sarah Johnson' in plan.stakeholders

        assert 'React SPA frontend' in plan.architecture_direction
        assert 'Client requests' in plan.architecture_direction

        assert 'React.js chosen for component reuse' in plan.technology_decisions
        assert 'Vue.js rejected' in plan.technology_decisions

        assert 'Phase 1: Research & Design' in plan.plan_structure

        assert '1 Plan Manager, 2 Frontend Developers' in plan.resource_requirements

        assert 'Timeline delays due to design complexity' in plan.risk_management

        assert 'WCAG 2.1 AA accessibility compliance' in plan.quality_assurance
        assert 'Unit testing (90% coverage)' in plan.quality_assurance
        assert 'All user stories complete' in plan.quality_assurance

        assert plan.plan_status == PlanStatus.APPROVED

    def test_parse_markdown_handles_missing_sections(self) -> None:
        markdown = """# Plan Plan: Simple Website

## Executive Summary

### Vision
Create a simple business website

### Mission
Provide online presence for small business

### Timeline
3 months

### Budget
$50,000

## Metadata

### Status
draft
"""

        plan = Plan.parse_markdown(markdown)

        assert plan.plan_name == 'Simple Website'
        assert 'Create a simple business website' in plan.executive_summary
        assert plan.business_objectives == 'Business Objectives not specified'
        assert plan.resource_requirements == 'Resource Requirements not specified'

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = """This is not a project plan format"""

        with pytest.raises(ValueError, match='Invalid plan format: missing title'):
            Plan.parse_markdown(invalid_markdown)

    def test_parse_preserves_custom_h3_subsections(self) -> None:
        markdown = """# Plan: Foundation

## Architecture Direction

### Architecture Overview
Microservice architecture with API gateway

### Data Flow
Client → API → Database

### Notion Data Model
11 kanban columns, 18 job card fields with auto/manual population rules

### Cost Monitoring
Monthly budget alerts via DigitalOcean

## Metadata

### Status
draft
"""
        plan = Plan.parse_markdown(markdown)

        assert '### Architecture Overview' in plan.architecture_direction
        assert '### Data Flow' in plan.architecture_direction
        assert '### Notion Data Model' in plan.architecture_direction
        assert '11 kanban columns' in plan.architecture_direction
        assert '### Cost Monitoring' in plan.architecture_direction


class TestPlanMarkdownBuilding:
    @pytest.fixture
    def sample_plan(self) -> Plan:
        return Plan(
            plan_name='E-Learning Platform',
            executive_summary=(
                '### Vision\n'
                'Create an accessible online learning platform for professional development\n\n'
                '### Mission\n'
                'Deliver high-quality educational content through modern technology\n\n'
                '### Timeline\n'
                '12 months from inception to full deployment\n\n'
                '### Budget\n'
                '$750,000 including development, content, and marketing'
            ),
            business_objectives=(
                '### Primary Objectives\n'
                'Launch platform with 100+ courses, achieve 1000+ active learners, 90% completion rate\n\n'
                '### Success Metrics\n'
                'User engagement >70%, course completion >90%, customer satisfaction >4.8/5\n\n'
                '### Key Performance Indicators\n'
                'Monthly active users, course completion rates, user retention, revenue growth'
            ),
            plan_scope=(
                '### Included Features\n'
                'Video streaming, interactive quizzes, progress tracking, certificates, mobile app\n\n'
                '### Anti-Requirements\n'
                'No live streaming, no social features, no advanced analytics\n\n'
                '### Assumptions\n'
                'Market demand exists, content creators available\n\n'
                '### Constraints\n'
                'Budget limit $750k, 12-month timeline'
            ),
            stakeholders=(
                '### Plan Sponsor\n'
                'Chief Learning Officer - Dr. Emily Chen\n\n'
                '### Key Stakeholders\n'
                'Learning & Development team, IT department, Content creators\n\n'
                '### End Users\n'
                'Corporate learners, HR administrators, learning coordinators'
            ),
            architecture_direction=(
                '### Architecture Overview\n'
                'React frontend, Django REST API, PostgreSQL, S3 for video storage\n\n'
                '### Data Flow\n'
                'Learner → React SPA → Django API → PostgreSQL/S3'
            ),
            technology_decisions=(
                '### Chosen Technologies\n'
                'React chosen for rich UI, Django chosen for team expertise\n\n'
                '### Rejected Technologies\n'
                'Vue.js rejected (team unfamiliar), MongoDB rejected (relational data model required)'
            ),
            plan_structure=(
                '### Work Breakdown\n'
                'Planning (1 month), Development (8 months), Content creation (6 months)\n\n'
                '### Phases Overview\n'
                'Requirements gathering, platform development, content integration, testing, launch\n\n'
                '### Dependencies\n'
                'Content creation timeline, video hosting service, payment gateway integration'
            ),
            resource_requirements=(
                '### Team Structure\n'
                '1 PM, 3 Developers, 1 Designer, 2 QA, 1 DevOps, 2 Content specialists\n\n'
                '### Technology Requirements\n'
                'React frontend, Django backend, PostgreSQL, AWS services, video CDN\n\n'
                '### Infrastructure Needs\n'
                'AWS cloud hosting, video streaming infrastructure, CDN, monitoring tools'
            ),
            risk_management=(
                '### Identified Risks\n'
                'Content creation delays, technical complexity, user adoption challenges\n\n'
                '### Mitigation Strategies\n'
                'Early content planning, agile development, user testing, market research\n\n'
                '### Contingency Plans\n'
                'Reduced feature set, extended timeline, additional resources'
            ),
            quality_assurance=(
                '### Quality Bar\n'
                '90% test coverage, SCORM compliance, WCAG 2.1 AA accessibility, sub-3s page loads\n\n'
                '### Testing Strategy\n'
                'Automated testing, user acceptance testing, performance testing, security audits\n\n'
                '### Acceptance Criteria\n'
                'All features functional, performance targets met, security approval, content uploaded'
            ),
            plan_status=PlanStatus.ACTIVE,
        )

    def test_build_markdown_creates_valid_template_format(self, sample_plan: Plan) -> None:
        markdown = sample_plan.build_markdown()

        assert '# Plan: E-Learning Platform' in markdown
        assert '## Executive Summary' in markdown
        assert '### Vision' in markdown
        assert 'Create an accessible online learning platform' in markdown
        assert '## Business Objectives' in markdown
        assert '### Primary Objectives' in markdown
        assert 'Launch platform with 100+ courses' in markdown
        assert '## Architecture Direction' in markdown
        assert '### Architecture Overview' in markdown
        assert '## Technology Decisions' in markdown
        assert '### Chosen Technologies' in markdown
        assert '## Resource Requirements' in markdown
        assert '### Team Structure' in markdown
        assert '1 PM, 3 Developers, 1 Designer' in markdown
        assert '## Quality Assurance' in markdown
        assert '### Quality Bar' in markdown
        assert '### Status\nactive' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_plan: Plan) -> None:
        markdown = sample_plan.build_markdown()
        parsed_plan = Plan.parse_markdown(markdown)

        assert parsed_plan.plan_name == sample_plan.plan_name
        assert parsed_plan.executive_summary == sample_plan.executive_summary
        assert parsed_plan.business_objectives == sample_plan.business_objectives
        assert parsed_plan.plan_scope == sample_plan.plan_scope
        assert parsed_plan.stakeholders == sample_plan.stakeholders
        assert parsed_plan.architecture_direction == sample_plan.architecture_direction
        assert parsed_plan.technology_decisions == sample_plan.technology_decisions
        assert parsed_plan.plan_structure == sample_plan.plan_structure
        assert parsed_plan.resource_requirements == sample_plan.resource_requirements
        assert parsed_plan.risk_management == sample_plan.risk_management
        assert parsed_plan.quality_assurance == sample_plan.quality_assurance
        assert parsed_plan.plan_status == sample_plan.plan_status

    def test_character_for_character_round_trip_validation(self, sample_plan: Plan) -> None:
        original_markdown = sample_plan.build_markdown()
        parsed_plan = Plan.parse_markdown(original_markdown)
        rebuilt_markdown = parsed_plan.build_markdown()

        assert original_markdown == rebuilt_markdown

    def test_round_trip_preserves_custom_h3_subsections(self) -> None:
        plan = Plan(
            plan_name='Foundation',
            architecture_direction=(
                '### Architecture Overview\nMicroservice architecture\n\n'
                '### Data Flow\nClient → API → DB\n\n'
                '### Notion Data Model\n11 kanban columns, 18 job card fields\n\n'
                '### Cost Monitoring\nMonthly budget alerts'
            ),
            quality_assurance=(
                '### Quality Bar\n90% test coverage\n\n'
                '### Testing Strategy\nUnit + integration tests\n\n'
                '### Acceptance Criteria\nAll tests passing\n\n'
                '### Maintainability\nDocs, runbook, dependency lifecycle'
            ),
        )

        markdown = plan.build_markdown()
        parsed = Plan.parse_markdown(markdown)

        assert '### Notion Data Model' in parsed.architecture_direction
        assert '11 kanban columns' in parsed.architecture_direction
        assert '### Cost Monitoring' in parsed.architecture_direction
        assert '### Maintainability' in parsed.quality_assurance
        assert 'runbook' in parsed.quality_assurance

        rebuilt = parsed.build_markdown()
        assert markdown == rebuilt


class TestPlanAdditionalSections:
    def test_parse_markdown_captures_additional_sections(self) -> None:
        markdown = """# Plan: Test Plan

## Executive Summary

### Vision
Test vision

### Mission
Test mission

### Timeline
Test timeline

### Budget
Test budget

## Security and Secrets Management

All secrets stored in DO Functions encrypted env vars.
Rotation cadence: quarterly.

## Dependency Lifecycle Management

Uses uv lock. Monthly audits. Minor version pinning.

## Metadata

### Status
draft
"""
        plan = Plan.parse_markdown(markdown)

        assert plan.additional_sections is not None
        assert 'Security and Secrets Management' in plan.additional_sections
        assert 'encrypted env vars' in plan.additional_sections['Security and Secrets Management']
        assert 'Dependency Lifecycle Management' in plan.additional_sections
        assert 'uv lock' in plan.additional_sections['Dependency Lifecycle Management']

    def test_build_markdown_renders_additional_sections(self) -> None:
        plan = Plan(
            plan_name='Test Plan',
            additional_sections={
                'Security': 'Secrets in encrypted env vars',
                'Scalability': 'Single-user architecture by design',
            },
        )
        markdown = plan.build_markdown()

        assert '## Security' in markdown
        assert 'Secrets in encrypted env vars' in markdown
        assert '## Scalability' in markdown
        assert 'Single-user architecture by design' in markdown
        security_pos = markdown.index('## Security')
        metadata_pos = markdown.index('## Metadata')
        assert security_pos < metadata_pos

    def test_build_markdown_without_additional_sections(self) -> None:
        plan = Plan(plan_name='Test Plan')
        markdown = plan.build_markdown()

        assert '## Metadata' in markdown
        sections = [line for line in markdown.split('\n') if line.startswith('## ')]
        assert sections[-1] == '## Metadata'

    def test_round_trip_preserves_additional_sections(self) -> None:
        plan = Plan(
            plan_name='Roundtrip Test',
            additional_sections={
                'Security and Secrets Management': 'DO Functions encrypted env vars\nRotation: quarterly',
                'Dependency Lifecycle': 'uv lock, monthly audits',
            },
        )

        markdown = plan.build_markdown()
        parsed = Plan.parse_markdown(markdown)

        assert parsed.additional_sections is not None
        assert 'Security and Secrets Management' in parsed.additional_sections
        assert 'Dependency Lifecycle' in parsed.additional_sections
        assert 'encrypted env vars' in parsed.additional_sections['Security and Secrets Management']

        rebuilt = parsed.build_markdown()
        assert markdown == rebuilt
