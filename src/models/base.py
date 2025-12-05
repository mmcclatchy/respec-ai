import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Self

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import BaseModel


class MCPModel(BaseModel, ABC):
    # Class variables - won't be treated as model fields
    TITLE_PATTERN: ClassVar[str] = ''
    TITLE_FIELD: ClassVar[str] = ''
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {}

    @classmethod
    def _find_nodes_by_type(cls, node: SyntaxTreeNode, node_type: str) -> list[SyntaxTreeNode]:
        nodes = []

        if node.type == node_type:
            nodes.append(node)

        if hasattr(node, 'children') and node.children:
            for child in node.children:
                nodes.extend(cls._find_nodes_by_type(child, node_type))

        return nodes

    @classmethod
    def _extract_text_content(cls, node: SyntaxTreeNode) -> str:
        if not hasattr(node, 'children') or not node.children:
            return getattr(node, 'content', '')

        return ' '.join(cls._extract_text_content(child) for child in node.children)

    @classmethod
    def _extract_content_from_raw_markdown(cls, markdown: str, path: tuple[str, ...]) -> str:
        """Extract content from raw markdown between headers, preserving all formatting.

        This extracts the raw markdown text between headers without parsing,
        preserving code blocks, lists, blockquotes, and all other formatting.
        """
        h2_header = path[0]
        h3_header = path[1] if len(path) > 1 else None

        lines = markdown.split('\n')

        # Find h2 header
        h2_idx = None
        for i, line in enumerate(lines):
            if line.startswith('## ') and h2_header in line:
                h2_idx = i
                break

        if h2_idx is None:
            return ''

        # If no h3 specified, get content from h2 until next h2
        if h3_header is None:
            content_lines = []
            for i in range(h2_idx + 1, len(lines)):
                if lines[i].startswith('## '):
                    break
                content_lines.append(lines[i])

            content = '\n'.join(content_lines).strip()
            return content if content else ''

        # Find h3 header after h2
        h3_idx = None
        for i in range(h2_idx + 1, len(lines)):
            if lines[i].startswith('## '):
                break  # Stop at next h2
            if lines[i].startswith('### ') and h3_header in lines[i]:
                h3_idx = i
                break

        if h3_idx is None:
            return ''

        # Extract content from h3 until next h2 or h3
        content_lines = []
        for i in range(h3_idx + 1, len(lines)):
            if lines[i].startswith('## ') or lines[i].startswith('### '):
                break
            content_lines.append(lines[i])

        content = '\n'.join(content_lines).strip()
        return content if content else ''

    @classmethod
    def _extract_content_by_header_path(cls, tree: SyntaxTreeNode, path: tuple[str, ...]) -> str:
        h2_header = path[0]
        h3_header = path[1] if len(path) > 1 else None

        nodes = tree.children if hasattr(tree, 'children') else []
        h2_start_idx = None

        for i, node in enumerate(nodes):
            if node.type == 'heading' and node.tag == 'h2':
                header_text = cls._extract_text_content(node).strip()
                if header_text == h2_header:
                    h2_start_idx = i
                    break

        if h2_start_idx is None:
            return ''

        if h3_header is None:
            content_parts = []
            for j in range(h2_start_idx + 1, len(nodes)):
                next_node = nodes[j]
                if next_node.type == 'heading' and next_node.tag == 'h2':
                    break
                if next_node.type in [
                    'paragraph',
                    'list',
                    'bullet_list',
                    'ordered_list',
                    'blockquote',
                    'code_block',
                    'fence',
                ]:
                    content_parts.append(cls._extract_text_content(next_node).strip())
            return '\n\n'.join(content_parts).strip()

        h3_start_idx = None
        for j in range(h2_start_idx + 1, len(nodes)):
            next_node = nodes[j]
            if next_node.type == 'heading' and next_node.tag == 'h2':
                break
            if next_node.type == 'heading' and next_node.tag == 'h3':
                header_text = cls._extract_text_content(next_node).strip()
                if header_text == h3_header:
                    h3_start_idx = j
                    break

        if h3_start_idx is None:
            return ''

        content_parts = []
        for j in range(h3_start_idx + 1, len(nodes)):
            next_node = nodes[j]
            if next_node.type == 'heading' and next_node.tag in ['h2', 'h3']:
                break
            if next_node.type in [
                'paragraph',
                'list',
                'bullet_list',
                'ordered_list',
                'blockquote',
                'code_block',
                'fence',
            ]:
                content_parts.append(cls._extract_text_content(next_node).strip())

        return '\n\n'.join(content_parts).strip()

    @classmethod
    def _extract_list_items_by_header_path(cls, tree: SyntaxTreeNode, path: tuple[str, ...]) -> list[str]:
        h2_header = path[0]
        h3_header = path[1] if len(path) > 1 else None

        nodes = tree.children if hasattr(tree, 'children') else []
        h2_start_idx = None

        for i, node in enumerate(nodes):
            if node.type == 'heading' and node.tag == 'h2':
                header_text = cls._extract_text_content(node).strip()
                if header_text == h2_header:
                    h2_start_idx = i
                    break

        if h2_start_idx is None:
            return []

        if h3_header is None:
            for j in range(h2_start_idx + 1, len(nodes)):
                next_node = nodes[j]
                if next_node.type == 'heading' and next_node.tag == 'h2':
                    break
                if next_node.type == 'bullet_list':
                    items = []
                    for item in cls._find_nodes_by_type(next_node, 'list_item'):
                        item_text = cls._extract_text_content(item).strip()
                        if item_text and item_text not in ['None identified', 'None provided']:
                            items.append(item_text)
                    return items
            return []

        h3_start_idx = None
        for j in range(h2_start_idx + 1, len(nodes)):
            next_node = nodes[j]
            if next_node.type == 'heading' and next_node.tag == 'h2':
                break
            if next_node.type == 'heading' and next_node.tag == 'h3':
                header_text = cls._extract_text_content(next_node).strip()
                if header_text == h3_header:
                    h3_start_idx = j
                    break

        if h3_start_idx is None:
            return []

        for j in range(h3_start_idx + 1, len(nodes)):
            next_node = nodes[j]
            if next_node.type == 'heading' and next_node.tag in ['h2', 'h3']:
                break
            if next_node.type == 'bullet_list':
                items = []
                for item in cls._find_nodes_by_type(next_node, 'list_item'):
                    item_text = cls._extract_text_content(item).strip()
                    if item_text and item_text not in ['None identified', 'None provided']:
                        items.append(item_text)
                return items

        return []

    @classmethod
    def parse_markdown(cls, markdown: str) -> Self:
        if cls.TITLE_PATTERN not in markdown:
            # Convert class name from CamelCase to readable format
            readable_name = (
                cls.__name__.replace('Plan', ' Plan').replace('Spec', ' Spec').replace('Requirements', ' Requirements')
            )
            readable_name = ' '.join(readable_name.split()).lower()
            raise ValueError(f'Invalid {readable_name} format: missing title')

        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields: dict[str, Any] = {}

        # Extract title
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h1':
                continue
            title_text = cls._extract_text_content(node)
            title_pattern = cls.TITLE_PATTERN.replace('# ', '').split(':')[0]
            if title_pattern not in title_text:
                continue
            # Handle titles with and without colons
            if ':' in title_text:
                title_value = title_text.split(':', 1)[1].strip()
            else:
                # For titles without colons, use the full title text
                title_value = title_text.strip()

            # Validate strict kebab-case format for spec names
            if cls.TITLE_FIELD == 'phase_name' and not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', title_value):
                raise ValueError(
                    f"Invalid spec name format: '{title_value}'. "
                    f'Spec name must be lowercase kebab-case. '
                    f"Example: 'phase-1-foundation'"
                )

            fields[cls.TITLE_FIELD] = title_value
            break

        # Extract fields using header path mapping
        for field_name, header_path in cls.HEADER_FIELD_MAPPING.items():
            if field_name.endswith('_list'):
                # Handle list fields - extract as list and store under base field name
                base_field = field_name.replace('_list', '')
                extracted_list = cls._extract_list_items_by_header_path(tree, header_path)
                if extracted_list:  # Only set if we found actual content
                    # Store the list under the base field name
                    fields[base_field] = extracted_list
            else:
                # Handle content fields - extract raw markdown preserving all formatting
                extracted_content = cls._extract_content_from_raw_markdown(markdown, header_path)
                if extracted_content:  # Only set if we found actual content
                    fields[field_name] = extracted_content

        # Capture unmapped H2 sections in additional_sections (for models that support it)
        # Build set of mapped H2 headers
        mapped_h2_headers = {header_path[0] for header_path in cls.HEADER_FIELD_MAPPING.values()}

        # Find all H2 headers in markdown
        additional_sections: dict[str, str] = {}
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h2':
                continue
            h2_text = cls._extract_text_content(node).strip()

            # Skip if this H2 is in mapped headers or is Metadata
            if h2_text in mapped_h2_headers or h2_text == 'Metadata':
                continue

            # Extract content for this unmapped H2 section
            content = cls._extract_content_from_raw_markdown(markdown, (h2_text,))
            if content:  # Only store if there's actual content
                additional_sections[h2_text] = content

        # Set additional_sections if we found any unmapped sections
        if additional_sections:
            fields['additional_sections'] = additional_sections

        return cls(**fields)

    @abstractmethod
    def build_markdown(self) -> str:
        pass
