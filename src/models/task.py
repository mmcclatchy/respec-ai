from typing import ClassVar
from uuid import uuid4

from pydantic import Field

from .base import MCPModel


from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from typing import Any


class Task(MCPModel):
    TITLE_PATTERN: ClassVar[str] = '# Task'
    TITLE_FIELD: ClassVar[str] = 'name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'phase_path': ('Identity', 'Phase Path'),
        'description': ('Overview', 'Description'),
        'acceptance_criteria': ('Overview', 'Acceptance Criteria'),
        'mode': ('Overview', 'Mode'),
        'sequence': ('Overview', 'Sequence'),
        'dependencies': ('Overview', 'Dependencies'),
        'estimated_complexity': ('Overview', 'Estimated Complexity'),
        'implementation_notes': ('Implementation', 'Notes'),
        'test_strategy': ('Implementation', 'Test Strategy'),
        'status': ('Status', 'Current Status'),
        'iteration': ('Metadata', 'Iteration'),
        'version': ('Metadata', 'Version'),
    }

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    phase_path: str  # "plan-name/phase-name"

    # Definition
    description: str = 'Description not specified'
    acceptance_criteria: str = 'Acceptance criteria not specified'
    mode: str = 'implementation'  # "database" | "api" | "integration" | "test" | "implementation"

    # Sequencing
    sequence: int = 1
    dependencies: list[str] = Field(default_factory=list)
    estimated_complexity: str = 'medium'  # "low" | "medium" | "high"

    # Implementation
    implementation_notes: str | None = None
    test_strategy: str | None = None

    # Status
    status: str = 'pending'  # "pending" | "in_progress" | "completed"

    # Metadata
    iteration: int = 0
    version: int = 1

    @classmethod
    def parse_markdown(cls, markdown: str) -> 'Task':
        if cls.TITLE_PATTERN not in markdown:
            raise ValueError('Invalid task format: missing title')

        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields: dict[str, Any] = {}

        # Extract title
        # TITLE_PATTERN is "# Task" but _extract_text_content strips the "#", so check for "Task"
        title_pattern_text = cls.TITLE_PATTERN.replace('# ', '')
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h1':
                continue
            title_text = cls._extract_text_content(node)
            if title_pattern_text in title_text or title_text.startswith(title_pattern_text):
                if ':' in title_text:
                    fields[cls.TITLE_FIELD] = title_text.split(':', 1)[1].strip()
                else:
                    # If no colon, the whole text is the title
                    fields[cls.TITLE_FIELD] = title_text.replace(title_pattern_text, '').strip()
                break

        # Extract fields using header path mapping
        for field_name, header_path in cls.HEADER_FIELD_MAPPING.items():
            extracted_content = cls._extract_content_from_raw_markdown(markdown, header_path)
            if extracted_content:
                fields[field_name] = extracted_content

        # Post-process specific fields for type conversion
        # Convert dependencies string to list
        if 'dependencies' in fields:
            deps_str = fields['dependencies'].strip()
            if deps_str.lower() in ('none', '', '[]'):
                fields['dependencies'] = []
            else:
                fields['dependencies'] = [d.strip() for d in deps_str.split(',') if d.strip()]

        # Convert numeric fields from string to int
        for int_field in ['sequence', 'iteration', 'version']:
            if int_field in fields and isinstance(fields[int_field], str):
                fields[int_field] = int(fields[int_field].strip())

        return cls(**fields)

    def build_markdown(self) -> str:
        sections = [f'{self.TITLE_PATTERN}: {self.name}']

        sections.append('\n## Identity')
        sections.append(f'\n### Phase Path\n{self.phase_path}')

        sections.append('\n## Overview')
        sections.append(f'\n### Description\n{self.description}')
        sections.append(f'\n### Acceptance Criteria\n{self.acceptance_criteria}')
        sections.append(f'\n### Mode\n{self.mode}')
        sections.append(f'\n### Sequence\n{self.sequence}')

        deps_str = ', '.join(self.dependencies) if self.dependencies else 'None'
        sections.append(f'\n### Dependencies\n{deps_str}')
        sections.append(f'\n### Estimated Complexity\n{self.estimated_complexity}')

        if self.implementation_notes or self.test_strategy:
            sections.append('\n## Implementation')
            if self.implementation_notes:
                sections.append(f'\n### Notes\n{self.implementation_notes}')
            if self.test_strategy:
                sections.append(f'\n### Test Strategy\n{self.test_strategy}')

        sections.append('\n## Status')
        sections.append(f'\n### Current Status\n{self.status}')

        sections.append('\n## Metadata')
        sections.append(f'\n### Iteration\n{self.iteration}')
        sections.append(f'\n### Version\n{self.version}')

        return '\n'.join(sections) + '\n'
