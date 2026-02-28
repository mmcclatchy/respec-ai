import asyncio
import inspect
import re
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from fastmcp import FastMCP


@dataclass
class ParameterDoc:
    name: str
    type_str: str
    description: str
    required: bool


@dataclass
class ToolDocumentation:
    name: str
    brief_description: str
    parameters: list[ParameterDoc]
    return_type: str
    full_docstring: str

    def format_signature(self) -> str:
        params_str = ', '.join(f'{p.name}: {p.type_str}' for p in self.parameters)
        return f'{self.name}({params_str}) -> {self.return_type}'

    def format_inline_doc(self) -> str:
        return f'**Tool**: `{self.format_signature()}`\n{self.brief_description}'

    def format_reference_doc(self) -> str:
        params_section = '\n'.join(f'- `{p.name}` ({p.type_str}): {p.description}' for p in self.parameters)

        return f"""### {self.name}
**Signature**: `{self.format_signature()}`
**Purpose**: {self.brief_description}
**Parameters**:
{params_section}
**Returns**: {self.return_type}"""


class ToolDocumentationExtractor:
    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
        self._tool_cache: dict[str, ToolDocumentation] = {}

    def get_tool_documentation(self, tool_name: str) -> ToolDocumentation:
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name]

        tool_func = self._get_tool_function(tool_name)
        if not tool_func:
            raise ValueError(f"Tool '{tool_name}' not found in MCP registry")

        doc = self._extract_documentation(tool_name, tool_func)
        self._tool_cache[tool_name] = doc
        return doc

    def get_all_tool_docs(self) -> dict[str, ToolDocumentation]:
        tool_names = self._list_tool_names()
        return {name: self.get_tool_documentation(name) for name in tool_names}

    def _get_tool_function(self, tool_name: str) -> Any:
        try:
            tools_dict = asyncio.run(self.mcp.get_tools())
            if tool_name in tools_dict:
                return tools_dict[tool_name].fn
        except Exception:
            pass

        return None

    def _list_tool_names(self) -> list[str]:
        try:
            tools_dict = asyncio.run(self.mcp.get_tools())
            return list(tools_dict.keys())
        except Exception:
            return []

    def _extract_documentation(self, tool_name: str, func: Any) -> ToolDocumentation:
        sig = inspect.signature(func)
        docstring = inspect.getdoc(func) or ''

        brief_description = self._extract_brief_description(docstring)
        parameters = self._extract_parameters(sig, docstring)
        return_type = self._format_type(sig.return_annotation)

        return ToolDocumentation(
            name=tool_name,
            brief_description=brief_description,
            parameters=parameters,
            return_type=return_type,
            full_docstring=docstring,
        )

    def _extract_brief_description(self, docstring: str) -> str:
        if not docstring:
            return 'No description available'

        lines = docstring.strip().split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(('Parameters:', 'Returns:', 'Args:', 'Return:')):
                return stripped

        return lines[0].strip() if lines else 'No description available'

    def _extract_parameters(self, sig: inspect.Signature, docstring: str) -> list[ParameterDoc]:
        param_descriptions = self._parse_param_descriptions(docstring)
        parameters = []

        for param_name, param in sig.parameters.items():
            if param_name == 'ctx':
                continue

            type_str = self._format_type(param.annotation)
            description = param_descriptions.get(param_name, '')
            required = param.default == inspect.Parameter.empty

            parameters.append(
                ParameterDoc(
                    name=param_name,
                    type_str=type_str,
                    description=description,
                    required=required,
                )
            )

        return parameters

    def _parse_param_descriptions(self, docstring: str) -> dict[str, str]:
        if not docstring:
            return {}

        descriptions = {}
        lines = docstring.split('\n')
        in_params_section = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith(('Parameters:', 'Args:')):
                in_params_section = True
                continue

            if stripped.startswith(('Returns:', 'Return:', 'Raises:', 'Examples:')):
                in_params_section = False
                continue

            if in_params_section and stripped:
                match = re.match(r'^-?\s*(\w+)(?:\s*\([^)]+\))?\s*:\s*(.+)', stripped)
                if match:
                    param_name, param_desc = match.groups()
                    descriptions[param_name] = param_desc.strip()

        return descriptions

    def _format_type(self, annotation: Any) -> str:
        if annotation == inspect.Parameter.empty or annotation is None:
            return 'Any'

        if hasattr(annotation, '__name__'):
            return annotation.__name__

        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)

            if origin is type(None):
                return 'None'

            if hasattr(origin, '__name__'):
                origin_name = origin.__name__
            else:
                origin_name = str(origin).replace('typing.', '')

            if args:
                args_str = ', '.join(self._format_type(arg) for arg in args)
                if origin_name == 'Union':
                    return ' | '.join(self._format_type(arg) for arg in args)
                return f'{origin_name}[{args_str}]'

            return origin_name

        return str(annotation).replace('typing.', '')
