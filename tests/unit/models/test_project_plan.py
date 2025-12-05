import pytest
from src.models.enums import ProjectStatus
from src.models.project_plan import ProjectPlan


class TestProjectPlanParsing:
    def test_parse_markdown_extracts_all_fields(self) -> None:
        markdown = """# Project Plan: Customer Portal Redesign

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

## Project Scope

### Included Features
User dashboard redesign, mobile responsive design, self-service features, account management tools

### Excluded Features
Legacy system migration, third-party integrations, advanced analytics dashboard

### Assumptions
Existing infrastructure can support new portal, customers will adopt new design, no major security changes needed

### Constraints
Must maintain 99.9% uptime during migration, limited to current technology stack, budget cap at $400k

## Stakeholders

### Project Sponsor
Chief Technology Officer - Sarah Johnson, provides strategic direction and final approvals

### Key Stakeholders
Customer Success team, IT Operations, Security team, Executive leadership, Customer Advisory Board

### End Users
Existing customers (5000+ active users), customer support representatives, account managers

## Project Structure

### Work Breakdown
Phase 1: Research & Design (2 months), Phase 2: Development (4 months), Phase 3: Testing & Launch (2 months)

### Phases Overview
Discovery and user research, UI/UX design, frontend development, backend API updates, testing, deployment

### Dependencies
Design system completion, API documentation updates, security review approval, infrastructure scaling

## Resource Requirements

### Team Structure
1 Project Manager, 2 Frontend Developers, 1 Backend Developer, 1 UI/UX Designer, 1 QA Engineer

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

### Quality Standards
WCAG 2.1 AA accessibility compliance, mobile-first responsive design, 99.9% uptime requirement

### Testing Strategy
Unit testing (90% coverage), integration testing, user acceptance testing, performance testing, security testing

### Acceptance Criteria
All user stories complete, performance benchmarks met, security scan passed, stakeholder sign-off received

## Communication Plan

### Reporting Structure
Weekly status reports to sponsor, bi-weekly stakeholder updates, monthly executive briefings

### Meeting Schedule
Daily standups, weekly team meetings, bi-weekly stakeholder reviews, monthly steering committee

### Documentation Standards
Confluence for project docs, Jira for task tracking, GitHub for code documentation, shared drive for assets

## Metadata

### Status
approved

### Created
2024-01-15

### Last Updated
2024-02-01

### Version
2.1
"""

        project_plan = ProjectPlan.parse_markdown(markdown)

        assert project_plan.project_name == 'Customer Portal Redesign'
        assert project_plan.project_vision == 'Transform customer experience through modern, intuitive portal design'
        assert (
            project_plan.project_mission
            == 'Deliver a user-friendly portal that increases customer satisfaction and reduces support tickets'
        )
        assert project_plan.project_timeline == '8 months from project kickoff to production deployment'
        assert project_plan.project_budget == '$400,000 including development, design, and infrastructure costs'

        # Business objectives
        assert 'Improve customer satisfaction scores by 30%' in project_plan.primary_objectives
        assert 'Customer satisfaction score >4.5/5' in project_plan.success_metrics
        assert 'Daily active users, session duration' in project_plan.key_performance_indicators

        # Project scope
        assert 'User dashboard redesign, mobile responsive design' in project_plan.included_features
        assert 'Legacy system migration, third-party integrations' in project_plan.excluded_features
        assert 'Existing infrastructure can support new portal' in project_plan.project_assumptions
        assert 'Must maintain 99.9% uptime during migration' in project_plan.project_constraints

        # Stakeholders
        assert 'Chief Technology Officer - Sarah Johnson' in project_plan.project_sponsor
        assert 'Customer Success team, IT Operations' in project_plan.key_stakeholders
        assert 'Existing customers (5000+ active users)' in project_plan.end_users

        # Project structure
        assert 'Phase 1: Research & Design (2 months)' in project_plan.work_breakdown
        assert 'Discovery and user research, UI/UX design' in project_plan.phases_overview
        assert 'Design system completion, API documentation' in project_plan.project_dependencies

        # Resource requirements
        assert '1 Project Manager, 2 Frontend Developers' in project_plan.team_structure
        assert 'React.js frontend, Node.js backend' in project_plan.technology_requirements
        assert 'Additional AWS instances, CDN setup' in project_plan.infrastructure_needs

        # Risk management
        assert 'Timeline delays due to design complexity' in project_plan.identified_risks
        assert 'Regular design reviews, early integration testing' in project_plan.mitigation_strategies
        assert 'Simplified design fallback, manual processes' in project_plan.contingency_plans

        # Quality assurance
        assert 'WCAG 2.1 AA accessibility compliance' in project_plan.quality_standards
        assert 'Unit testing (90% coverage), integration testing' in project_plan.testing_strategy
        assert 'All user stories complete, performance benchmarks met' in project_plan.acceptance_criteria

        # Communication plan
        assert 'Weekly status reports to sponsor' in project_plan.reporting_structure
        assert 'Daily standups, weekly team meetings' in project_plan.meeting_schedule
        assert 'Confluence for project docs, Jira for task tracking' in project_plan.documentation_standards

        # Metadata
        assert project_plan.project_status == ProjectStatus.APPROVED

    def test_parse_markdown_handles_missing_sections(self) -> None:
        markdown = """# Project Plan: Simple Website

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

### Created
2024-01-01

### Last Updated
2024-01-01

### Version
1.0
"""

        project_plan = ProjectPlan.parse_markdown(markdown)

        assert project_plan.project_name == 'Simple Website'
        assert project_plan.project_vision == 'Create a simple business website'
        # Missing sections should have default values
        assert 'Primary Objectives not specified' in project_plan.primary_objectives
        assert 'Success Metrics not specified' in project_plan.success_metrics
        assert 'Team Structure not specified' in project_plan.team_structure

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = """This is not a project plan format"""

        with pytest.raises(ValueError, match='Invalid project plan format: missing title'):
            ProjectPlan.parse_markdown(invalid_markdown)


class TestProjectPlanMarkdownBuilding:
    @pytest.fixture
    def sample_project_plan(self) -> ProjectPlan:
        return ProjectPlan(
            project_name='E-Learning Platform',
            project_vision='Create an accessible online learning platform for professional development',
            project_mission='Deliver high-quality educational content through modern technology',
            project_timeline='12 months from inception to full deployment',
            project_budget='$750,000 including development, content, and marketing',
            primary_objectives='Launch platform with 100+ courses, achieve 1000+ active learners, 90% completion rate',
            success_metrics='User engagement >70%, course completion >90%, customer satisfaction >4.8/5',
            key_performance_indicators='Monthly active users, course completion rates, user retention, revenue growth',
            included_features='Video streaming, interactive quizzes, progress tracking, certificates, mobile app',
            excluded_features='Live streaming, social features, advanced analytics, third-party integrations',
            project_assumptions='Market demand exists, content creators available, technology infrastructure scalable',
            project_constraints='Budget limit $750k, 12-month timeline, existing team size, regulatory compliance',
            project_sponsor='Chief Learning Officer - Dr. Emily Chen, oversees educational strategy and budget',
            key_stakeholders='Learning & Development team, IT department, Content creators, Executive leadership',
            end_users='Corporate learners, HR administrators, learning coordinators, subject matter experts',
            work_breakdown='Planning (1 month), Development (8 months), Content creation (6 months), Testing (2 months)',
            phases_overview='Requirements gathering, platform development, content integration, testing, launch',
            project_dependencies='Content creation timeline, video hosting service, payment gateway integration',
            team_structure='1 PM, 3 Developers, 1 Designer, 2 QA, 1 DevOps, 2 Content specialists',
            technology_requirements='React frontend, Django backend, PostgreSQL, AWS services, video CDN',
            infrastructure_needs='AWS cloud hosting, video streaming infrastructure, CDN, monitoring tools',
            identified_risks='Content creation delays, technical complexity, user adoption challenges, competition',
            mitigation_strategies='Early content planning, agile development, user testing, market research',
            contingency_plans='Reduced feature set, extended timeline, additional resources, alternative vendors',
            quality_standards='SCORM compliance, accessibility standards, mobile optimization, security best practices',
            testing_strategy='Automated testing, user acceptance testing, performance testing, security audits',
            acceptance_criteria='All features functional, performance targets met, security approval, content uploaded',
            reporting_structure='Weekly team updates, bi-weekly sponsor reviews, monthly board presentations',
            meeting_schedule='Daily standups, weekly planning, bi-weekly demos, monthly stakeholder meetings',
            documentation_standards='Technical docs in GitBook, project tracking in Asana, code docs in GitHub',
            project_status=ProjectStatus.ACTIVE,
        )

    def test_build_markdown_creates_valid_template_format(self, sample_project_plan: ProjectPlan) -> None:
        markdown = sample_project_plan.build_markdown()

        assert '# Project Plan: E-Learning Platform' in markdown
        assert '## Executive Summary' in markdown
        assert '### Vision' in markdown
        assert 'Create an accessible online learning platform for professional development' in markdown
        assert '## Business Objectives' in markdown
        assert '### Primary Objectives' in markdown
        assert 'Launch platform with 100+ courses, achieve 1000+ active learners, 90% completion rate' in markdown
        assert '## Resource Requirements' in markdown
        assert '### Team Structure' in markdown
        assert '1 PM, 3 Developers, 1 Designer, 2 QA, 1 DevOps, 2 Content specialists' in markdown
        assert '## Quality Assurance' in markdown
        assert '### Quality Standards' in markdown
        assert '### Status\nactive' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_project_plan: ProjectPlan) -> None:
        # Build markdown from the model
        markdown = sample_project_plan.build_markdown()

        # Parse it back into a model
        parsed_project_plan = ProjectPlan.parse_markdown(markdown)

        # Should match original (except timestamps)
        assert parsed_project_plan.project_name == sample_project_plan.project_name
        assert parsed_project_plan.project_vision == sample_project_plan.project_vision
        assert parsed_project_plan.project_mission == sample_project_plan.project_mission
        assert parsed_project_plan.project_timeline == sample_project_plan.project_timeline
        assert parsed_project_plan.project_budget == sample_project_plan.project_budget
        assert parsed_project_plan.primary_objectives == sample_project_plan.primary_objectives
        assert parsed_project_plan.success_metrics == sample_project_plan.success_metrics
        assert parsed_project_plan.key_performance_indicators == sample_project_plan.key_performance_indicators
        assert parsed_project_plan.included_features == sample_project_plan.included_features
        assert parsed_project_plan.excluded_features == sample_project_plan.excluded_features
        assert parsed_project_plan.project_assumptions == sample_project_plan.project_assumptions
        assert parsed_project_plan.project_constraints == sample_project_plan.project_constraints
        assert parsed_project_plan.project_sponsor == sample_project_plan.project_sponsor
        assert parsed_project_plan.key_stakeholders == sample_project_plan.key_stakeholders
        assert parsed_project_plan.end_users == sample_project_plan.end_users
        assert parsed_project_plan.work_breakdown == sample_project_plan.work_breakdown
        assert parsed_project_plan.phases_overview == sample_project_plan.phases_overview
        assert parsed_project_plan.project_dependencies == sample_project_plan.project_dependencies
        assert parsed_project_plan.team_structure == sample_project_plan.team_structure
        assert parsed_project_plan.technology_requirements == sample_project_plan.technology_requirements
        assert parsed_project_plan.infrastructure_needs == sample_project_plan.infrastructure_needs
        assert parsed_project_plan.identified_risks == sample_project_plan.identified_risks
        assert parsed_project_plan.mitigation_strategies == sample_project_plan.mitigation_strategies
        assert parsed_project_plan.contingency_plans == sample_project_plan.contingency_plans
        assert parsed_project_plan.quality_standards == sample_project_plan.quality_standards
        assert parsed_project_plan.testing_strategy == sample_project_plan.testing_strategy
        assert parsed_project_plan.acceptance_criteria == sample_project_plan.acceptance_criteria
        assert parsed_project_plan.reporting_structure == sample_project_plan.reporting_structure
        assert parsed_project_plan.meeting_schedule == sample_project_plan.meeting_schedule
        assert parsed_project_plan.documentation_standards == sample_project_plan.documentation_standards
        assert parsed_project_plan.project_status == sample_project_plan.project_status

    def test_character_for_character_round_trip_validation(self, sample_project_plan: ProjectPlan) -> None:
        # Build markdown
        original_markdown = sample_project_plan.build_markdown()

        # Parse and rebuild
        parsed_project_plan = ProjectPlan.parse_markdown(original_markdown)
        rebuilt_markdown = parsed_project_plan.build_markdown()

        # Should be identical
        assert original_markdown == rebuilt_markdown
