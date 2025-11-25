from typing import ClassVar

from pydantic import Field

from services.utils.errors import SpecNotFoundError

from .base import MCPModel
from .enums import RoadmapStatus
from .spec import TechnicalSpec


class Roadmap(MCPModel):
    # Class configuration for MCPModel
    TITLE_PATTERN: ClassVar[str] = '# Project Roadmap'
    TITLE_FIELD: ClassVar[str] = 'project_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'project_goal': ('Project Details', 'Project Goal'),
        'total_duration': ('Project Details', 'Total Duration'),
        'team_size': ('Project Details', 'Team Size'),
        'roadmap_budget': ('Project Details', 'Budget'),
        'critical_path_analysis': ('Risk Assessment', 'Critical Path Analysis'),
        'key_risks': ('Risk Assessment', 'Key Risks'),
        'mitigation_plans': ('Risk Assessment', 'Mitigation Plans'),
        'buffer_time': ('Risk Assessment', 'Buffer Time'),
        'development_resources': ('Resource Planning', 'Development Resources'),
        'infrastructure_requirements': ('Resource Planning', 'Infrastructure Requirements'),
        'external_dependencies': ('Resource Planning', 'External Dependencies'),
        'quality_assurance_plan': ('Resource Planning', 'Quality Assurance Plan'),
        'technical_milestones': ('Success Metrics', 'Technical Milestones'),
        'business_milestones': ('Success Metrics', 'Business Milestones'),
        'quality_gates': ('Success Metrics', 'Quality Gates'),
        'performance_targets': ('Success Metrics', 'Performance Targets'),
        'roadmap_status': ('Metadata', 'Status'),
        'spec_count': ('Metadata', 'Spec Count'),
    }

    # Model fields with defaults
    project_name: str = 'Unnamed Project'
    project_goal: str = 'Project Goal not specified'
    total_duration: str = 'Total Duration not specified'
    team_size: str = 'Team Size not specified'
    roadmap_budget: str = 'Budget not specified'
    specs: list[TechnicalSpec] = Field(default_factory=list)
    critical_path_analysis: str = 'Critical Path Analysis not specified'
    key_risks: str = 'Key Risks not specified'
    mitigation_plans: str = 'Mitigation Plans not specified'
    buffer_time: str = 'Buffer Time not specified'
    development_resources: str = 'Development Resources not specified'
    infrastructure_requirements: str = 'Infrastructure Requirements not specified'
    external_dependencies: str = 'External Dependencies not specified'
    quality_assurance_plan: str = 'Quality Assurance Plan not specified'
    technical_milestones: str = 'Technical Milestones not specified'
    business_milestones: str = 'Business Milestones not specified'
    quality_gates: str = 'Quality Gates not specified'
    performance_targets: str = 'Performance Targets not specified'
    roadmap_status: RoadmapStatus = RoadmapStatus.DRAFT
    spec_count: int = 0

    def build_markdown(self) -> str:
        roadmap_metadata = f"""{self.TITLE_PATTERN}: {self.project_name}

## Project Details

### Project Goal
{self.project_goal}

### Total Duration
{self.total_duration}

### Team Size
{self.team_size}

### Budget
{self.roadmap_budget}

## Risk Assessment

### Critical Path Analysis
{self.critical_path_analysis}

### Key Risks
{self.key_risks}

### Mitigation Plans
{self.mitigation_plans}

### Buffer Time
{self.buffer_time}

## Resource Planning

### Development Resources
{self.development_resources}

### Infrastructure Requirements
{self.infrastructure_requirements}

### External Dependencies
{self.external_dependencies}

### Quality Assurance Plan
{self.quality_assurance_plan}

## Success Metrics

### Technical Milestones
{self.technical_milestones}

### Business Milestones
{self.business_milestones}

### Quality Gates
{self.quality_gates}

### Performance Targets
{self.performance_targets}

## Metadata

### Status
{self.roadmap_status.value}

### Spec Count
{self.spec_count}
"""
        # Append full TechnicalSpec markdown for round-trip consistency
        if self.specs:
            specs_markdown = '\n\n'.join(spec.build_markdown() for spec in self.specs)
            return roadmap_metadata + '\n' + specs_markdown

        return roadmap_metadata

    def get_spec_name(self, spec_name: str) -> str:
        for spec in self.specs:
            if spec.phase_name == spec_name:
                return spec.phase_name

        raise SpecNotFoundError(f'Spec not found: {spec_name}')

    def add_spec(self, spec: TechnicalSpec) -> None:
        # Remove existing spec with same name if it exists
        for i, existing_spec in enumerate(self.specs):
            if existing_spec.phase_name == spec.phase_name:
                self.specs[i] = spec  # Replace existing
                return

        # Add new spec
        self.specs.append(spec)
        self.spec_count = len(self.specs)
