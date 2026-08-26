import re
import typing
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Self

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import BaseModel


def _is_list_annotation(annotation: Any) -> bool:
    """Whether a field holds a list, including inside `list[str] | None` unions.

    Field routing in `parse_markdown` keys on this rather than on a field-name suffix:
    a name-based rule silently mis-routes any field whose name merely resembles the
    convention, and the extracted value then lands under a key that is not a model field.
    """
    if annotation is None:
        return False
    origin = typing.get_origin(annotation)
    if origin is list:
        return True
    if origin is not None:
        return any(_is_list_annotation(arg) for arg in typing.get_args(annotation))
    return False


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

        # If no h3 specified, get content from h2 until next h2 or markdown separator
        if h3_header is None:
            content_lines = []
            for i in range(h2_idx + 1, len(lines)):
                if lines[i].startswith('## ') or lines[i].strip() == '---':
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

        # Extract content from h3 until next h2 or h3 or markdown separator
        content_lines = []
        for i in range(h3_idx + 1, len(lines)):
            if lines[i].startswith('## ') or lines[i].startswith('### ') or lines[i].strip() == '---':
                break
            content_lines.append(lines[i])

        content = '\n'.join(content_lines).strip()
        return content if content else ''

    @classmethod
    def _trim_at_legitimate_separator(cls, section_lines: list[str]) -> list[str]:
        """Drop a bare '---' and everything after it, but only when that '---' is a
        legitimate document boundary rather than the F8 truncation defect.

        Generated markdown legitimately uses a bare '---' to mark the end of a document
        before concatenated content that isn't part of it (e.g. RoadmapTools.store joins
        a roadmap and its phases on '# Phase:', see test_markdown_separator_handling.py).
        That is a boundary, not loss, when what follows the '---' is blank or is itself
        another document's H1 title. Anything else after a bare '---' is genuinely
        orphaned content the user wrote and the parser would silently drop (F8).
        """
        separator_idx = next((i for i, line in enumerate(section_lines) if line.strip() == '---'), None)
        if separator_idx is None:
            return section_lines

        trailing = [line for line in section_lines[separator_idx + 1 :] if line.strip()]
        if not trailing or trailing[0].startswith('# '):
            return section_lines[:separator_idx]

        return section_lines

    @classmethod
    def _extract_raw_section_verbatim(cls, markdown: str, path: tuple[str, ...]) -> str:
        """Ground truth for what the user actually wrote under a heading path.

        Unlike `_extract_content_from_raw_markdown`, this matches heading text exactly
        rather than by substring, and only drops a bare '---' when it is a legitimate
        document boundary rather than the F8 truncation defect. It exists so
        `find_content_loss` can detect findings F7-F9 by comparing this against what
        the (unrepaired) parser actually captures.
        """
        h2_header = path[0]
        h3_header = path[1] if len(path) > 1 else None

        lines = markdown.split('\n')

        h2_idx = next(
            (i for i, line in enumerate(lines) if line.startswith('## ') and line[3:].strip() == h2_header), None
        )
        if h2_idx is None:
            return ''

        if h3_header is None:
            end = next((i for i in range(h2_idx + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
            section_lines = cls._trim_at_legitimate_separator(lines[h2_idx + 1 : end])
            return '\n'.join(section_lines).strip()

        h3_idx = None
        for i in range(h2_idx + 1, len(lines)):
            if lines[i].startswith('## '):
                break
            if lines[i].startswith('### ') and lines[i][4:].strip() == h3_header:
                h3_idx = i
                break

        if h3_idx is None:
            return ''

        end = next(
            (
                i
                for i in range(h3_idx + 1, len(lines))
                if lines[i].startswith('## ') or lines[i].startswith('### ')
            ),
            len(lines),
        )
        section_lines = cls._trim_at_legitimate_separator(lines[h3_idx + 1 : end])
        return '\n'.join(section_lines).strip()

    @classmethod
    def _find_orphan_h3_headings(cls, markdown: str) -> list[str]:
        """H3 headings under a mapped H2 that have no landing spot in the mapping (F9).

        Metadata is excluded to match parse_markdown's own special-casing of it
        (base.py additional_sections capture skips 'Metadata' outright) - it holds
        model-managed state fields, not user-authored content.
        """
        mapped_h3_by_h2: dict[str, set[str]] = {}
        for header_path in cls.HEADER_FIELD_MAPPING.values():
            if len(header_path) > 1:
                mapped_h3_by_h2.setdefault(header_path[0], set()).add(header_path[1])
        mapped_h3_by_h2.pop('Metadata', None)

        orphans: list[str] = []
        current_h2: str | None = None
        for line in markdown.split('\n'):
            if line.startswith('## '):
                current_h2 = line[3:].strip()
            elif line.startswith('### ') and current_h2 in mapped_h3_by_h2:
                h3_text = line[4:].strip()
                if h3_text not in mapped_h3_by_h2[current_h2]:
                    orphans.append(f'{current_h2} > {h3_text}')

        return orphans

    @classmethod
    def find_content_loss(cls, markdown: str) -> list[str]:
        """Report headings whose content the parser would silently drop or truncate.

        Does not change parsing behavior - `parse_markdown` still truncates on a bare
        '---' and still drops orphan H3s. This only tells the caller where it happened,
        so a human hand-editing a document at a gate is told rather than overwritten.
        """
        issues: list[str] = []

        for header_path in cls.HEADER_FIELD_MAPPING.values():
            ground_truth = cls._extract_raw_section_verbatim(markdown, header_path)
            captured = cls._extract_content_from_raw_markdown(markdown, header_path)
            if ground_truth and ground_truth != captured:
                heading = ' > '.join(header_path)
                issues.append(f'{heading}: content present in the input is missing or truncated after parsing')

        for orphan_heading in cls._find_orphan_h3_headings(markdown):
            issues.append(f'{orphan_heading}: not a recognized field under this section and will be dropped')

        return issues

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
                cls.__name__.replace('Plan', ' Plan')
                .replace('Phase', ' Phase')
                .replace('Requirements', ' Requirements')
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

            # Validate strict kebab-case format for phase names
            if cls.TITLE_FIELD == 'phase_name' and not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', title_value):
                raise ValueError(
                    f"Invalid phase name format: '{title_value}'. "
                    f'Phase name must be lowercase kebab-case. '
                    f"Example: 'phase-1-foundation'"
                )

            fields[cls.TITLE_FIELD] = title_value
            break

        # Extract fields using header path mapping
        for field_name, header_path in cls.HEADER_FIELD_MAPPING.items():
            field_info = cls.model_fields.get(field_name)
            if field_info is not None and _is_list_annotation(field_info.annotation):
                extracted_list = cls._extract_list_items_by_header_path(tree, header_path)
                if extracted_list:
                    fields[field_name] = extracted_list
            else:
                # Raw extraction preserves formatting the tree walker would flatten
                extracted_content = cls._extract_content_from_raw_markdown(markdown, header_path)
                if extracted_content:
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
