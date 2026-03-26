from typing import Any, ClassVar
from uuid import uuid4

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import Field

from .base import MCPModel


class Task(MCPModel):
    TITLE_PATTERN: ClassVar[str] = '# Task'
    TITLE_FIELD: ClassVar[str] = 'name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'identity': ('Identity',),
        'overview': ('Overview',),
        'implementation': ('Implementation',),
        'quality': ('Quality',),
        'research': ('Research',),
        'status': ('Status', 'Current Status'),
        'active': ('Metadata', 'Active'),
        'version': ('Metadata', 'Version'),
    }

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    phase_path: str = ''

    identity: str = 'Identity not specified'
    overview: str = 'Overview not specified'
    implementation: str = 'Implementation not specified'
    quality: str = 'Quality not specified'
    research: str = 'Research not specified'

    status: str = 'pending'
    active: bool = True
    version: str = '1.0'

    @classmethod
    def parse_markdown(cls, markdown: str) -> 'Task':
        if cls.TITLE_PATTERN not in markdown:
            raise ValueError('Invalid task format: missing title')

        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields: dict[str, Any] = {}

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

        for field_name, header_path in cls.HEADER_FIELD_MAPPING.items():
            extracted_content = cls._extract_content_from_raw_markdown(markdown, header_path)
            if extracted_content:
                fields[field_name] = extracted_content

        if 'active' in fields:
            active_str = fields['active'].strip().lower()
            fields['active'] = active_str in ('true', 'yes', '1')

        if 'identity' in fields:
            identity_lines = fields['identity'].split('\n')
            for i, line in enumerate(identity_lines):
                if '### Phase Path' in line:
                    for j in range(i + 1, len(identity_lines)):
                        stripped = identity_lines[j].strip()
                        if stripped:
                            fields['phase_path'] = stripped
                            break
                    break

        return cls(**fields)

    def build_markdown(self) -> str:
        sections = [
            f"""{self.TITLE_PATTERN}: {self.name}

## Identity

{self.identity}

## Overview

{self.overview}

## Implementation

{self.implementation}

## Quality

{self.quality}

## Research

{self.research}

## Status

### Current Status
{self.status}

## Metadata

### Active
{'true' if self.active else 'false'}

### Version
{self.version}"""
        ]

        return '\n'.join(sections) + '\n'
