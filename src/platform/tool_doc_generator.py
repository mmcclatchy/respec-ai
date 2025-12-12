from src.platform.tool_doc_extractor import ToolDocumentation
from src.platform.tool_enums import RespecAITool


class ToolDocGenerator:
    @staticmethod
    def generate_inline_doc(tool_doc: ToolDocumentation, include_description: bool = True) -> str:
        if include_description:
            return tool_doc.format_inline_doc()
        return f'**Tool**: `{tool_doc.format_signature()}`'

    @staticmethod
    def generate_reference_section(tool_docs: list[ToolDocumentation]) -> str:
        if not tool_docs:
            return ''

        header = '## MCP Tool Reference\n\n'
        tool_sections = [tool_doc.format_reference_doc() for tool_doc in tool_docs]

        return header + '\n\n'.join(tool_sections)

    @staticmethod
    def generate_tools_yaml_with_docs(tools: list[str], tool_docs: dict[str, ToolDocumentation]) -> str:
        yaml_lines = []

        for tool_name in tools:
            if tool_name in tool_docs:
                doc = tool_docs[tool_name]
                yaml_lines.append(f'  - {tool_name}  # {doc.brief_description}')
            else:
                yaml_lines.append(f'  - {tool_name}')

        return '\n'.join(yaml_lines)

    @staticmethod
    def generate_tool_call_inline(tool: RespecAITool, **kwargs: str) -> str:
        """Generate inline tool call with parameters.

        Args:
            tool: The RespecAITool enum value
            **kwargs: Parameter name-value pairs (values as strings)

        Returns:
            Formatted tool call string like: mcp__respec-ai__get_document(doc_type="task", loop_id=planning_loop_id)

        Example:
            generate_tool_call_inline(
                RespecAITool.GET_DOCUMENT,
                doc_type='"task"',
                loop_id='planning_loop_id'
            )
            # Returns: mcp__respec-ai__get_document(doc_type="task", loop_id=planning_loop_id)
        """
        if not kwargs:
            return f'{tool}()'

        params = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        return f'{tool}({params})'
