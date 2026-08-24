from typing import ClassVar
from uuid import uuid4

from pydantic import Field

from .base import MCPModel
from .enums import PhaseStatus, ShapeGate


class Phase(MCPModel):
    # Class configuration for MCPModel
    TITLE_PATTERN: ClassVar[str] = '# Phase'
    TITLE_FIELD: ClassVar[str] = 'phase_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'objectives': ('Overview', 'Objectives'),
        'scope': ('Overview', 'Scope'),
        'dependencies': ('Overview', 'Dependencies'),
        'deliverables': ('Overview', 'Deliverables'),
        'architecture': ('System Design', 'Architecture'),
        'technology_stack': ('System Design', 'Technology Stack'),
        'system_design_additional': ('System Design', 'System Design - Additional Sections'),
        'module_layout': ('Design Shape', 'Module Layout'),
        'skeleton_index': ('Design Shape', 'Skeleton Index'),
        'collaboration_and_wiring': ('Design Shape', 'Collaboration And Wiring'),
        'test_list': ('Design Shape', 'Test List'),
        'design_shape_additional': ('Design Shape', 'Design Shape - Additional Sections'),
        'open_design_decisions': ('Design Decisions', 'Open Design Decisions'),
        'settled_design_decisions': ('Design Decisions', 'Settled Design Decisions'),
        'functional_requirements': ('Implementation', 'Functional Requirements'),
        'non_functional_requirements': ('Implementation', 'Non-Functional Requirements'),
        'development_plan': ('Implementation', 'Development Plan'),
        'testing_strategy': ('Implementation', 'Testing Strategy'),
        'implementation_additional': ('Implementation', 'Implementation - Additional Sections'),
        'implementation_plan_references': ('Additional Details', 'Implementation Plan References'),
        'research_requirements': ('Additional Details', 'Research Requirements'),
        'success_criteria': ('Additional Details', 'Success Criteria'),
        'integration_context': ('Additional Details', 'Integration Context'),
        'additional_details_additional': ('Additional Details', 'Additional Details - Additional Sections'),
        'iteration': ('Metadata', 'Iteration'),
        'version': ('Metadata', 'Version'),
        'phase_status': ('Metadata', 'Status'),
        'shape_gate': ('Metadata', 'Shape Gate'),
    }

    # Model fields
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    phase_name: str

    # Immutable initial state fields (set at iteration=0, preserved thereafter)
    objectives: str = Field(default='Objectives not specified', frozen=True)
    scope: str = Field(default='Scope not specified', frozen=True)
    dependencies: str = Field(default='Dependencies not specified', frozen=True)
    deliverables: str = Field(default='Deliverables not specified', frozen=True)

    # Optional fields (added by phase-architect in iteration 1+)
    architecture: str | None = None
    technology_stack: str | None = None
    functional_requirements: str | None = None
    non_functional_requirements: str | None = None
    development_plan: str | None = None
    testing_strategy: str | None = None
    implementation_plan_references: str | None = None
    research_requirements: str | None = None
    success_criteria: str | None = None
    integration_context: str | None = None

    # Design layer (added by phase-architect; consumed by coder and spec-alignment-reviewer)
    module_layout: str | None = None
    skeleton_index: str | None = None
    collaboration_and_wiring: str | None = None
    test_list: str | None = None
    open_design_decisions: str | None = None
    settled_design_decisions: str | None = None

    system_design_additional: str | None = None
    design_shape_additional: str | None = None
    implementation_additional: str | None = None
    additional_details_additional: str | None = None

    # Flexible storage for domain-specific sections
    # Examples: {"Data Models": "content", "API Design": "content", "CLI Commands": "content"}
    additional_sections: dict[str, str] | None = None

    # State tracking
    iteration: int = 0
    version: int = 1
    phase_status: PhaseStatus = PhaseStatus.DRAFT
    shape_gate: ShapeGate = ShapeGate.UNSHAPED

    def build_markdown(self) -> str:
        sections = [f'{self.TITLE_PATTERN}: {self.phase_name}']

        sections.append('\n## Overview')
        sections.append(f'\n### Objectives\n{self.objectives}')
        sections.append(f'\n### Scope\n{self.scope}')
        sections.append(f'\n### Dependencies\n{self.dependencies}')
        sections.append(f'\n### Deliverables\n{self.deliverables}')

        if self.architecture or self.technology_stack or self.system_design_additional:
            sections.append('\n## System Design')
            if self.architecture:
                sections.append(f'\n### Architecture\n{self.architecture}')
            if self.technology_stack:
                sections.append(f'\n### Technology Stack\n{self.technology_stack}')
            if self.system_design_additional:
                sections.append(f'\n### System Design - Additional Sections\n{self.system_design_additional}')

        if (
            self.module_layout
            or self.skeleton_index
            or self.collaboration_and_wiring
            or self.test_list
            or self.design_shape_additional
        ):
            sections.append('\n## Design Shape')
            if self.module_layout:
                sections.append(f'\n### Module Layout\n{self.module_layout}')
            if self.skeleton_index:
                sections.append(f'\n### Skeleton Index\n{self.skeleton_index}')
            if self.collaboration_and_wiring:
                sections.append(f'\n### Collaboration And Wiring\n{self.collaboration_and_wiring}')
            if self.test_list:
                sections.append(f'\n### Test List\n{self.test_list}')
            if self.design_shape_additional:
                sections.append(f'\n### Design Shape - Additional Sections\n{self.design_shape_additional}')

        if self.open_design_decisions or self.settled_design_decisions:
            sections.append('\n## Design Decisions')
            if self.open_design_decisions:
                sections.append(f'\n### Open Design Decisions\n{self.open_design_decisions}')
            if self.settled_design_decisions:
                sections.append(f'\n### Settled Design Decisions\n{self.settled_design_decisions}')

        if (
            self.functional_requirements
            or self.non_functional_requirements
            or self.development_plan
            or self.testing_strategy
            or self.implementation_additional
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
            if self.implementation_additional:
                sections.append(f'\n### Implementation - Additional Sections\n{self.implementation_additional}')

        if (
            self.implementation_plan_references
            or self.research_requirements
            or self.success_criteria
            or self.integration_context
            or self.additional_details_additional
        ):
            sections.append('\n## Additional Details')
            if self.implementation_plan_references:
                sections.append(f'\n### Implementation Plan References\n{self.implementation_plan_references}')
            if self.research_requirements:
                sections.append(f'\n### Research Requirements\n{self.research_requirements}')
            if self.success_criteria:
                sections.append(f'\n### Success Criteria\n{self.success_criteria}')
            if self.integration_context:
                sections.append(f'\n### Integration Context\n{self.integration_context}')
            if self.additional_details_additional:
                sections.append(f'\n### Additional Details - Additional Sections\n{self.additional_details_additional}')

        # Include additional sections before metadata
        if self.additional_sections:
            for section_name, content in self.additional_sections.items():
                sections.append(f'\n## {section_name}\n{content}')

        sections.append('\n## Metadata')
        sections.append(f'\n### Iteration\n{self.iteration}')
        sections.append(f'\n### Version\n{self.version}')
        sections.append(f'\n### Status\n{self.phase_status.value}')
        sections.append(f'\n### Shape Gate\n{self.shape_gate.value}')

        return '\n'.join(sections) + '\n'
