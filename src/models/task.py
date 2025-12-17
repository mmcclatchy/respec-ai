from typing import Any, ClassVar
from uuid import uuid4

from pydantic import Field

from .base import MCPModel

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


class Task(MCPModel):
    """Unified Task model - a complete implementation document with Checklist and Steps.

    This model consolidates the previous TaskBreakdown and Task models into
    a single document that contains:
    - Overview: goal, acceptance criteria, tech stack
    - Implementation: checklist (prioritized todos) + steps (### Step N: sections)
    - Quality: testing strategy
    - Status and metadata

    Steps are stored as raw markdown within the implementation_steps field,
    preserving all formatting and structure.
    """

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

    # Status management
    status: str = 'pending'  # "pending" | "in_progress" | "completed"
    active: bool = True  # For lifecycle management (soft delete)

    # Metadata
    version: str = '1.0'

    @classmethod
    def parse_markdown(cls, markdown: str) -> 'Task':
        if cls.TITLE_PATTERN not in markdown:
            raise ValueError('Invalid task format: missing title')

        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields: dict[str, Any] = {}

        # Extract title
        title_pattern_text = cls.TITLE_PATTERN.replace('# ', '')
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h1':
                continue
            title_text = cls._extract_text_content(node)
            if title_pattern_text in title_text or title_text.startswith(title_pattern_text):
                if ':' in title_text:
                    fields[cls.TITLE_FIELD] = title_text.split(':', 1)[1].strip()
                else:
                    fields[cls.TITLE_FIELD] = title_text.replace(title_pattern_text, '').strip()
                break

        # Extract fields using header path mapping
        for field_name, header_path in cls.HEADER_FIELD_MAPPING.items():
            extracted_content = cls._extract_content_from_raw_markdown(markdown, header_path)
            if extracted_content:
                fields[field_name] = extracted_content

        # Post-process specific fields for type conversion
        # Convert active string to bool
        if 'active' in fields:
            active_str = fields['active'].strip().lower()
            fields['active'] = active_str in ('true', 'yes', '1')

        return cls(**fields)

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

        sections.append('\n## Status')
        sections.append(f'\n### Current Status\n{self.status}')

        sections.append('\n## Metadata')
        active_str = 'true' if self.active else 'false'
        sections.append(f'\n### Active\n{active_str}')
        sections.append(f'\n### Version\n{self.version}')

        return '\n'.join(sections) + '\n'
