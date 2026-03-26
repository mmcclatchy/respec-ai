from typing import ClassVar

from .base import MCPModel
from .enums import PlanStatus


class Plan(MCPModel):
    TITLE_PATTERN: ClassVar[str] = '# Plan'
    TITLE_FIELD: ClassVar[str] = 'plan_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'executive_summary': ('Executive Summary',),
        'business_objectives': ('Business Objectives',),
        'plan_scope': ('Plan Scope',),
        'stakeholders': ('Stakeholders',),
        'architecture_direction': ('Architecture Direction',),
        'technology_decisions': ('Technology Decisions',),
        'plan_structure': ('Plan Structure',),
        'resource_requirements': ('Resource Requirements',),
        'risk_management': ('Risk Management',),
        'quality_assurance': ('Quality Assurance',),
        'plan_status': ('Metadata', 'Status'),
    }

    plan_name: str = 'Unnamed Plan'
    executive_summary: str = 'Executive Summary not specified'
    business_objectives: str = 'Business Objectives not specified'
    plan_scope: str = 'Plan Scope not specified'
    stakeholders: str = 'Stakeholders not specified'
    architecture_direction: str = 'Architecture Direction not specified'
    technology_decisions: str = 'Technology Decisions not specified'
    plan_structure: str = 'Plan Structure not specified'
    resource_requirements: str = 'Resource Requirements not specified'
    risk_management: str = 'Risk Management not specified'
    quality_assurance: str = 'Quality Assurance not specified'
    additional_sections: dict[str, str] | None = None
    plan_status: PlanStatus = PlanStatus.DRAFT

    def build_markdown(self) -> str:
        sections = [
            f"""{self.TITLE_PATTERN}: {self.plan_name}

## Executive Summary

{self.executive_summary}

## Business Objectives

{self.business_objectives}

## Plan Scope

{self.plan_scope}

## Stakeholders

{self.stakeholders}

## Architecture Direction

{self.architecture_direction}

## Technology Decisions

{self.technology_decisions}

## Plan Structure

{self.plan_structure}

## Resource Requirements

{self.resource_requirements}

## Risk Management

{self.risk_management}

## Quality Assurance

{self.quality_assurance}"""
        ]

        if self.additional_sections:
            for section_name, content in self.additional_sections.items():
                sections.append(f'\n## {section_name}\n\n{content}')

        sections.append(f'\n## Metadata\n\n### Status\n{self.plan_status.value}')

        return '\n'.join(sections) + '\n'
