from typing import ClassVar
from uuid import uuid4

from pydantic import Field

from .base import MCPModel


class Task(MCPModel):
    TITLE_PATTERN: ClassVar[str] = '# Task'
    TITLE_FIELD: ClassVar[str] = 'name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'phase_path': ('Identity', 'Phase Path'),
        'goal': ('Overview', 'Goal'),
        'acceptance_criteria': ('Overview', 'Acceptance Criteria'),
        'tech_stack_reference': ('Overview', 'Technology Stack Reference'),
        'implementation_checklist': ('Implementation', 'Checklist'),
        'implementation_steps': ('Implementation', 'Steps'),
        'testing_strategy': ('Quality', 'Testing Strategy'),
        'research': ('Research', 'Research Read Log'),
        'status': ('Status', 'Current Status'),
        'active': ('Metadata', 'Active'),
        'version': ('Metadata', 'Version'),
    }

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    phase_path: str  # "plan-name/phase-name"

    # What we're building
    goal: str = 'Goal not specified'
    acceptance_criteria: str = 'Acceptance criteria not specified'
    tech_stack_reference: str = 'Technology stack reference not specified'

    # How to build it
    implementation_checklist: str = 'Implementation checklist not specified'
    implementation_steps: str = 'Implementation steps not specified'

    # Quality assurance
    testing_strategy: str = 'Testing strategy not specified'

    research: str = 'Research not specified'
    additional_sections: dict[str, str] | None = None

    # Status management
    status: str = 'pending'  # "pending" | "in_progress" | "completed"
    active: bool = True  # For lifecycle management (soft delete)

    # Metadata
    version: str = '1.0'

    def build_markdown(self) -> str:
        sections = [f'{self.TITLE_PATTERN}: {self.name}']

        sections.append('\n## Identity')
        sections.append(f'\n### Phase Path\n{self.phase_path}')

        sections.append('\n## Overview')
        sections.append(f'\n### Goal\n{self.goal}')
        sections.append(f'\n### Acceptance Criteria\n{self.acceptance_criteria}')
        sections.append(f'\n### Technology Stack Reference\n{self.tech_stack_reference}')

        sections.append('\n## Implementation')
        sections.append(f'\n### Checklist\n{self.implementation_checklist}')
        sections.append(f'\n### Steps\n{self.implementation_steps}')

        sections.append('\n## Quality')
        sections.append(f'\n### Testing Strategy\n{self.testing_strategy}')

        sections.append('\n## Research')
        sections.append(f'\n### Research Read Log\n{self.research}')

        if self.additional_sections:
            for section_name, content in self.additional_sections.items():
                sections.append(f'\n## {section_name}\n{content}')

        sections.append('\n## Status')
        sections.append(f'\n### Current Status\n{self.status}')

        sections.append('\n## Metadata')
        active_str = 'true' if self.active else 'false'
        sections.append(f'\n### Active\n{active_str}')
        sections.append(f'\n### Version\n{self.version}')

        return '\n'.join(sections) + '\n'
