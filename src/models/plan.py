from typing import ClassVar

from .base import MCPModel
from .enums import PlanStatus


class Plan(MCPModel):
    # Class configuration
    TITLE_PATTERN: ClassVar[str] = '# Plan'
    TITLE_FIELD: ClassVar[str] = 'plan_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'project_vision': ('Executive Summary', 'Vision'),
        'project_mission': ('Executive Summary', 'Mission'),
        'project_timeline': ('Executive Summary', 'Timeline'),
        'project_budget': ('Executive Summary', 'Budget'),
        'primary_objectives': ('Business Objectives', 'Primary Objectives'),
        'success_metrics': ('Business Objectives', 'Success Metrics'),
        'key_performance_indicators': ('Business Objectives', 'Key Performance Indicators'),
        'included_features': ('Plan Scope', 'Included Features'),
        'anti_requirements': ('Plan Scope', 'Anti-Requirements'),
        'project_assumptions': ('Plan Scope', 'Assumptions'),
        'project_constraints': ('Plan Scope', 'Constraints'),
        'project_sponsor': ('Stakeholders', 'Plan Sponsor'),
        'key_stakeholders': ('Stakeholders', 'Key Stakeholders'),
        'end_users': ('Stakeholders', 'End Users'),
        'architecture_overview': ('Architecture Direction', 'Architecture Overview'),
        'data_flow': ('Architecture Direction', 'Data Flow'),
        'technology_decisions': ('Technology Decisions', 'Chosen Technologies'),
        'technology_rejections': ('Technology Decisions', 'Rejected Technologies'),
        'work_breakdown': ('Plan Structure', 'Work Breakdown'),
        'phases_overview': ('Plan Structure', 'Phases Overview'),
        'project_dependencies': ('Plan Structure', 'Dependencies'),
        'team_structure': ('Resource Requirements', 'Team Structure'),
        'technology_requirements': ('Resource Requirements', 'Technology Requirements'),
        'infrastructure_needs': ('Resource Requirements', 'Infrastructure Needs'),
        'identified_risks': ('Risk Management', 'Identified Risks'),
        'mitigation_strategies': ('Risk Management', 'Mitigation Strategies'),
        'contingency_plans': ('Risk Management', 'Contingency Plans'),
        'quality_bar': ('Quality Assurance', 'Quality Bar'),
        'testing_strategy': ('Quality Assurance', 'Testing Strategy'),
        'acceptance_criteria': ('Quality Assurance', 'Acceptance Criteria'),
        'plan_status': ('Metadata', 'Status'),
    }

    # Model fields with defaults
    plan_name: str = 'Unnamed Plan'
    project_vision: str = 'Project Vision not specified'
    project_mission: str = 'Project Mission not specified'
    project_timeline: str = 'Project Timeline not specified'
    project_budget: str = 'Project Budget not specified'
    primary_objectives: str = 'Primary Objectives not specified'
    success_metrics: str = 'Success Metrics not specified'
    key_performance_indicators: str = 'Key Performance Indicators not specified'
    included_features: str = 'Included Features not specified'
    anti_requirements: str = 'Anti-Requirements not specified'
    project_assumptions: str = 'Project Assumptions not specified'
    project_constraints: str = 'Project Constraints not specified'
    project_sponsor: str = 'Project Sponsor not specified'
    key_stakeholders: str = 'Key Stakeholders not specified'
    end_users: str = 'End Users not specified'
    architecture_overview: str = 'Architecture Overview not specified'
    data_flow: str = 'Data Flow not specified'
    technology_decisions: str = 'Technology Decisions not specified'
    technology_rejections: str = 'Technology Rejections not specified'
    work_breakdown: str = 'Work Breakdown not specified'
    phases_overview: str = 'Phases Overview not specified'
    project_dependencies: str = 'Project Dependencies not specified'
    team_structure: str = 'Team Structure not specified'
    technology_requirements: str = 'Technology Requirements not specified'
    infrastructure_needs: str = 'Infrastructure Needs not specified'
    identified_risks: str = 'Identified Risks not specified'
    mitigation_strategies: str = 'Mitigation Strategies not specified'
    contingency_plans: str = 'Contingency Plans not specified'
    quality_bar: str = 'Quality Bar not specified'
    testing_strategy: str = 'Testing Strategy not specified'
    acceptance_criteria: str = 'Acceptance Criteria not specified'
    additional_sections: dict[str, str] | None = None
    plan_status: PlanStatus = PlanStatus.DRAFT

    def build_markdown(self) -> str:
        sections = [
            f"""{self.TITLE_PATTERN}: {self.plan_name}

## Executive Summary

### Vision
{self.project_vision}

### Mission
{self.project_mission}

### Timeline
{self.project_timeline}

### Budget
{self.project_budget}

## Business Objectives

### Primary Objectives
{self.primary_objectives}

### Success Metrics
{self.success_metrics}

### Key Performance Indicators
{self.key_performance_indicators}

## Plan Scope

### Included Features
{self.included_features}

### Anti-Requirements
{self.anti_requirements}

### Assumptions
{self.project_assumptions}

### Constraints
{self.project_constraints}

## Stakeholders

### Plan Sponsor
{self.project_sponsor}

### Key Stakeholders
{self.key_stakeholders}

### End Users
{self.end_users}

## Architecture Direction

### Architecture Overview
{self.architecture_overview}

### Data Flow
{self.data_flow}

## Technology Decisions

### Chosen Technologies
{self.technology_decisions}

### Rejected Technologies
{self.technology_rejections}

## Plan Structure

### Work Breakdown
{self.work_breakdown}

### Phases Overview
{self.phases_overview}

### Dependencies
{self.project_dependencies}

## Resource Requirements

### Team Structure
{self.team_structure}

### Technology Requirements
{self.technology_requirements}

### Infrastructure Needs
{self.infrastructure_needs}

## Risk Management

### Identified Risks
{self.identified_risks}

### Mitigation Strategies
{self.mitigation_strategies}

### Contingency Plans
{self.contingency_plans}

## Quality Assurance

### Quality Bar
{self.quality_bar}

### Testing Strategy
{self.testing_strategy}

### Acceptance Criteria
{self.acceptance_criteria}"""
        ]

        if self.additional_sections:
            for section_name, content in self.additional_sections.items():
                sections.append(f'\n## {section_name}\n{content}')

        sections.append(f'\n## Metadata\n\n### Status\n{self.plan_status.value}')

        return '\n'.join(sections) + '\n'
