from typing import ClassVar

from .base import MCPModel
from .enums import ProjectStatus


class ProjectPlan(MCPModel):
    # Class configuration
    TITLE_PATTERN: ClassVar[str] = '# Project Plan'
    TITLE_FIELD: ClassVar[str] = 'project_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'project_vision': ('Executive Summary', 'Vision'),
        'project_mission': ('Executive Summary', 'Mission'),
        'project_timeline': ('Executive Summary', 'Timeline'),
        'project_budget': ('Executive Summary', 'Budget'),
        'primary_objectives': ('Business Objectives', 'Primary Objectives'),
        'success_metrics': ('Business Objectives', 'Success Metrics'),
        'key_performance_indicators': ('Business Objectives', 'Key Performance Indicators'),
        'included_features': ('Project Scope', 'Included Features'),
        'excluded_features': ('Project Scope', 'Excluded Features'),
        'project_assumptions': ('Project Scope', 'Assumptions'),
        'project_constraints': ('Project Scope', 'Constraints'),
        'project_sponsor': ('Stakeholders', 'Project Sponsor'),
        'key_stakeholders': ('Stakeholders', 'Key Stakeholders'),
        'end_users': ('Stakeholders', 'End Users'),
        'work_breakdown': ('Project Structure', 'Work Breakdown'),
        'phases_overview': ('Project Structure', 'Phases Overview'),
        'project_dependencies': ('Project Structure', 'Dependencies'),
        'team_structure': ('Resource Requirements', 'Team Structure'),
        'technology_requirements': ('Resource Requirements', 'Technology Requirements'),
        'infrastructure_needs': ('Resource Requirements', 'Infrastructure Needs'),
        'identified_risks': ('Risk Management', 'Identified Risks'),
        'mitigation_strategies': ('Risk Management', 'Mitigation Strategies'),
        'contingency_plans': ('Risk Management', 'Contingency Plans'),
        'quality_standards': ('Quality Assurance', 'Quality Standards'),
        'testing_strategy': ('Quality Assurance', 'Testing Strategy'),
        'acceptance_criteria': ('Quality Assurance', 'Acceptance Criteria'),
        'reporting_structure': ('Communication Plan', 'Reporting Structure'),
        'meeting_schedule': ('Communication Plan', 'Meeting Schedule'),
        'documentation_standards': ('Communication Plan', 'Documentation Standards'),
        'project_status': ('Metadata', 'Status'),
    }

    # Model fields with defaults
    project_name: str = 'Unnamed Project'
    project_vision: str = 'Project Vision not specified'
    project_mission: str = 'Project Mission not specified'
    project_timeline: str = 'Project Timeline not specified'
    project_budget: str = 'Project Budget not specified'
    primary_objectives: str = 'Primary Objectives not specified'
    success_metrics: str = 'Success Metrics not specified'
    key_performance_indicators: str = 'Key Performance Indicators not specified'
    included_features: str = 'Included Features not specified'
    excluded_features: str = 'Excluded Features not specified'
    project_assumptions: str = 'Project Assumptions not specified'
    project_constraints: str = 'Project Constraints not specified'
    project_sponsor: str = 'Project Sponsor not specified'
    key_stakeholders: str = 'Key Stakeholders not specified'
    end_users: str = 'End Users not specified'
    work_breakdown: str = 'Work Breakdown not specified'
    phases_overview: str = 'Phases Overview not specified'
    project_dependencies: str = 'Project Dependencies not specified'
    team_structure: str = 'Team Structure not specified'
    technology_requirements: str = 'Technology Requirements not specified'
    infrastructure_needs: str = 'Infrastructure Needs not specified'
    identified_risks: str = 'Identified Risks not specified'
    mitigation_strategies: str = 'Mitigation Strategies not specified'
    contingency_plans: str = 'Contingency Plans not specified'
    quality_standards: str = 'Quality Standards not specified'
    testing_strategy: str = 'Testing Strategy not specified'
    acceptance_criteria: str = 'Acceptance Criteria not specified'
    reporting_structure: str = 'Reporting Structure not specified'
    meeting_schedule: str = 'Meeting Schedule not specified'
    documentation_standards: str = 'Documentation Standards not specified'
    project_status: ProjectStatus = ProjectStatus.DRAFT

    def build_markdown(self) -> str:
        return f"""{self.TITLE_PATTERN}: {self.project_name}

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

## Project Scope

### Included Features
{self.included_features}

### Excluded Features
{self.excluded_features}

### Assumptions
{self.project_assumptions}

### Constraints
{self.project_constraints}

## Stakeholders

### Project Sponsor
{self.project_sponsor}

### Key Stakeholders
{self.key_stakeholders}

### End Users
{self.end_users}

## Project Structure

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

### Quality Standards
{self.quality_standards}

### Testing Strategy
{self.testing_strategy}

### Acceptance Criteria
{self.acceptance_criteria}

## Communication Plan

### Reporting Structure
{self.reporting_structure}

### Meeting Schedule
{self.meeting_schedule}

### Documentation Standards
{self.documentation_standards}

## Metadata

### Status
{self.project_status.value}
"""
