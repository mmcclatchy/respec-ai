from typing import ClassVar
from uuid import uuid4

from pydantic import Field

from .base import MCPModel
from .enums import SpecStatus


class TechnicalSpec(MCPModel):
    # Class configuration for MCPModel
    TITLE_PATTERN: ClassVar[str] = '# Technical Specification'
    TITLE_FIELD: ClassVar[str] = 'phase_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'objectives': ('Overview', 'Objectives'),
        'scope': ('Overview', 'Scope'),
        'dependencies': ('Overview', 'Dependencies'),
        'deliverables': ('Overview', 'Deliverables'),
        'architecture': ('System Design', 'Architecture'),
        'technology_stack': ('System Design', 'Technology Stack'),
        'functional_requirements': ('Implementation', 'Functional Requirements'),
        'non_functional_requirements': ('Implementation', 'Non-Functional Requirements'),
        'development_plan': ('Implementation', 'Development Plan'),
        'testing_strategy': ('Implementation', 'Testing Strategy'),
        'research_requirements': ('Additional Details', 'Research Requirements'),
        'success_criteria': ('Additional Details', 'Success Criteria'),
        'integration_context': ('Additional Details', 'Integration Context'),
        'iteration': ('Metadata', 'Iteration'),
        'version': ('Metadata', 'Version'),
        'spec_status': ('Metadata', 'Status'),
    }

    # Model fields
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    phase_name: str

    # Required fields (present in iteration=0)
    objectives: str = 'Objectives not specified'
    scope: str = 'Scope not specified'
    dependencies: str = 'Dependencies not specified'
    deliverables: str = 'Deliverables not specified'

    # Optional fields (added by spec-architect in iteration 1+)
    architecture: str | None = None
    technology_stack: str | None = None
    functional_requirements: str | None = None
    non_functional_requirements: str | None = None
    development_plan: str | None = None
    testing_strategy: str | None = None
    research_requirements: str | None = None
    success_criteria: str | None = None
    integration_context: str | None = None

    # Flexible storage for domain-specific sections
    # Examples: {"Data Models": "content", "API Design": "content", "CLI Commands": "content"}
    additional_sections: dict[str, str] | None = None

    # State tracking
    iteration: int = 0
    version: int = 1
    spec_status: SpecStatus = SpecStatus.DRAFT

    def build_markdown(self) -> str:
        sections = [f'{self.TITLE_PATTERN}: {self.phase_name}']

        sections.append('\n## Overview')
        sections.append(f'\n### Objectives\n{self.objectives}')
        sections.append(f'\n### Scope\n{self.scope}')
        sections.append(f'\n### Dependencies\n{self.dependencies}')
        sections.append(f'\n### Deliverables\n{self.deliverables}')

        if self.architecture or self.technology_stack:
            sections.append('\n## System Design')
            if self.architecture:
                sections.append(f'\n### Architecture\n{self.architecture}')
            if self.technology_stack:
                sections.append(f'\n### Technology Stack\n{self.technology_stack}')

        if (
            self.functional_requirements
            or self.non_functional_requirements
            or self.development_plan
            or self.testing_strategy
        ):
            sections.append('\n## Implementation')
            if self.functional_requirements:
                sections.append(f'\n### Functional Requirements\n{self.functional_requirements}')
            if self.non_functional_requirements:
                sections.append(f'\n### Non-Functional Requirements\n{self.non_functional_requirements}')
            if self.development_plan:
                sections.append(f'\n### Development Plan\n{self.development_plan}')
            if self.testing_strategy:
                sections.append(f'\n### Testing Strategy\n{self.testing_strategy}')

        if self.research_requirements or self.success_criteria or self.integration_context:
            sections.append('\n## Additional Details')
            if self.research_requirements:
                sections.append(f'\n### Research Requirements\n{self.research_requirements}')
            if self.success_criteria:
                sections.append(f'\n### Success Criteria\n{self.success_criteria}')
            if self.integration_context:
                sections.append(f'\n### Integration Context\n{self.integration_context}')

        # Include additional sections before metadata
        if self.additional_sections:
            for section_name, content in self.additional_sections.items():
                sections.append(f'\n## {section_name}\n{content}')

        sections.append('\n## Metadata')
        sections.append(f'\n### Iteration\n{self.iteration}')
        sections.append(f'\n### Version\n{self.version}')
        sections.append(f'\n### Status\n{self.spec_status.value}')

        return '\n'.join(sections) + '\n'
