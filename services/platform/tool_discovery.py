"""Tool discovery utilities for validating enum definitions against actual MCP tools."""

import inspect
import re
from typing import Any

from fastmcp import FastMCP

from services.mcp.tools import (
    build_plan_tools,
    feedback_tools_unified,
    loop_tools,
    plan_completion_report_tools,
    project_plan_tools,
    register_all_tools,
    roadmap_tools,
    spec_tools,
)

from .tool_enums import SpecAITool


def discover_registered_spec_ai_tools() -> set[str]:
    temp_mcp = FastMCP('discovery')
    register_all_tools(temp_mcp)

    tool_names = {f'mcp__spec-ai__{name}' for name in temp_mcp._tool_manager._tools.keys()}
    return tool_names


def validate_spec_ai_enum_completeness() -> dict[str, list[str]]:
    registered_tools = discover_registered_spec_ai_tools()
    enum_tools = {tool.value for tool in SpecAITool}

    missing_from_enum = registered_tools - enum_tools
    missing_from_registration = enum_tools - registered_tools

    return {
        'missing_from_enum': sorted(list(missing_from_enum)),
        'missing_from_registration': sorted(list(missing_from_registration)),
        'registered_tools': sorted(list(registered_tools)),
        'enum_tools': sorted(list(enum_tools)),
    }


def discover_tool_registration_functions() -> dict[str, list[str]]:
    modules = [
        loop_tools,
        feedback_tools_unified,
        project_plan_tools,
        plan_completion_report_tools,
        roadmap_tools,
        spec_tools,
        build_plan_tools,
    ]

    discovered_tools: dict[str, list[str]] = {}

    for module in modules:
        module_name = module.__name__.split('.')[-1]
        tools: list[str] = []

        for name, obj in inspect.getmembers(module):
            if not (name.startswith('register_') and callable(obj)):
                continue

            source = inspect.getsource(obj)
            tool_patterns = [
                r'@mcp\.tool\s*\(\s*["\']([^"\']+)["\']',
                r'def\s+([a-z_]+)\s*\(',
            ]

            for pattern in tool_patterns:
                matches = re.findall(pattern, source)
                tools.extend(f'mcp__spec-ai__{match}' for match in matches if not match.startswith('register_'))

        discovered_tools[module_name] = list(set(tools))

    return discovered_tools


def validate_tool_enum_against_codebase() -> dict[str, Any]:
    spec_ai_validation = validate_spec_ai_enum_completeness()
    tool_discovery = discover_tool_registration_functions()

    missing_from_enum = spec_ai_validation['missing_from_enum']
    missing_from_registration = spec_ai_validation['missing_from_registration']

    issues = []
    if missing_from_enum:
        issues.append(f'Tools missing from SpecAITool enum: {missing_from_enum}')

    if missing_from_registration:
        issues.append(f'Enum tools not found in registration: {missing_from_registration}')

    is_complete = not (missing_from_enum or missing_from_registration)

    return {
        'spec_ai_tools': spec_ai_validation,
        'tool_registration_discovery': tool_discovery,
        'validation_summary': {
            'spec_ai_enum_complete': is_complete,
            'issues': issues,
        },
    }


def generate_enum_updates_from_discovery() -> str:
    registered_tools = discover_registered_spec_ai_tools()
    enum_tools = {tool.value for tool in SpecAITool}

    missing_tools = registered_tools - enum_tools

    if not missing_tools:
        return '# SpecAITool enum is up to date'

    enum_additions = []
    for tool in sorted(missing_tools):
        # Convert tool name to enum constant name
        # mcp__spec-ai__some_tool_name -> SOME_TOOL_NAME
        enum_name = tool.replace('mcp__spec-ai__', '').upper()
        enum_additions.append(f'    {enum_name} = "{tool}"')

    enum_addition_lines = '\n'.join(enum_additions)
    return f"""# Add these entries to SpecAITool enum:
{enum_addition_lines}"""
