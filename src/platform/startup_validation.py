"""Startup validation utilities to catch enum/reality mismatches."""

import logging
from typing import Any

from fastmcp import FastMCP

from src.mcp.tools import register_all_tools

from .adapters import GitHubAdapter, LinearAdapter, MarkdownAdapter
from .tool_enums import ExternalPlatformTool, RespecAITool


logger = logging.getLogger(__name__)


class StartupValidationError(Exception):
    pass


def validate_respec_ai_tools_at_startup() -> dict[str, Any]:
    # Create a temporary MCP server to discover registered tools
    temp_mcp = FastMCP('validation')

    try:
        # Register all tools
        register_all_tools(temp_mcp)

        # Get registered tool names
        registered_tools = set()
        if hasattr(temp_mcp, '_tools'):
            registered_tools = set(temp_mcp._tools.keys())

        # Get enum tool names
        enum_tools = {tool for tool in RespecAITool}

        # Find mismatches
        missing_from_enum = registered_tools - enum_tools
        missing_from_registration = enum_tools - registered_tools

        validation_result: dict[str, Any] = {
            'success': len(missing_from_enum) == 0 and len(missing_from_registration) == 0,
            'registered_tools': sorted(registered_tools),
            'enum_tools': sorted(enum_tools),
            'missing_from_enum': sorted(missing_from_enum),
            'missing_from_registration': sorted(missing_from_registration),
            'issues': [],
        }

        if missing_from_enum:
            validation_result['issues'].append(
                f'Tools registered but missing from RespecAITool enum: {sorted(missing_from_enum)}'
            )

        if missing_from_registration:
            validation_result['issues'].append(
                f'Tools in RespecAITool enum but not registered: {sorted(missing_from_registration)}'
            )

        return validation_result

    except Exception as e:
        logger.error(f'Failed to validate respec-ai tools: {e}')
        return {'success': False, 'error': str(e), 'issues': [f'Validation failed with error: {e}']}


def validate_external_platform_tools() -> dict[str, Any]:
    validation_result: dict[str, Any] = {'success': True, 'issues': []}

    # Check that all Linear tools start with correct prefix
    linear_tools = [tool for tool in ExternalPlatformTool if tool.startswith('mcp__linear-server__')]
    github_tools = [tool for tool in ExternalPlatformTool if tool.startswith('mcp__github__')]

    # Basic validation
    if not linear_tools:
        validation_result['success'] = False
        validation_result['issues'].append('No Linear tools found in ExternalPlatformTool enum')

    if not github_tools:
        validation_result['success'] = False
        validation_result['issues'].append('No GitHub tools found in ExternalPlatformTool enum')

    # Check for naming consistency
    for tool in ExternalPlatformTool:
        if not (tool.startswith('mcp__linear-server__') or tool.startswith('mcp__github__')):
            validation_result['success'] = False
            validation_result['issues'].append(f'External platform tool has invalid prefix: {tool}')

    validation_result['linear_tools_count'] = len(linear_tools)
    validation_result['github_tools_count'] = len(github_tools)

    return validation_result


def validate_platform_adapters() -> dict[str, Any]:
    validation_result: dict[str, Any] = {'success': True, 'issues': []}

    required_properties = [
        'plan_sync_instructions',
        'phase_sync_instructions',
        'task_sync_instructions',
        'phase_discovery_instructions',
        'task_discovery_instructions',
        'coding_standards_location',
        'phase_location_hint',
        'task_location_hint',
        'create_plan_tool',
        'retrieve_plan_tool',
        'update_plan_tool',
        'create_plan_completion_tool',
        'create_phase_tool',
        'retrieve_phase_tool',
        'update_phase_tool',
        'comment_phase_tool',
        'create_task_tool',
        'retrieve_task_tool',
        'update_task_tool',
        'list_phases_tool',
        'list_tasks_tool',
    ]

    adapters = {
        'MarkdownAdapter': MarkdownAdapter(),
        'LinearAdapter': LinearAdapter(),
        'GitHubAdapter': GitHubAdapter(),
    }

    try:
        for adapter_name, adapter in adapters.items():
            for prop_name in required_properties:
                if not hasattr(adapter, prop_name):
                    validation_result['success'] = False
                    validation_result['issues'].append(f'{adapter_name} missing required property: {prop_name}')
                    continue

                try:
                    value = getattr(adapter, prop_name)
                    if not isinstance(value, str) or not value.strip():
                        validation_result['success'] = False
                        validation_result['issues'].append(f'{adapter_name}.{prop_name} must return non-empty string')
                except Exception as e:
                    validation_result['success'] = False
                    validation_result['issues'].append(f'{adapter_name}.{prop_name} failed: {e}')

        validation_result['adapters_count'] = len(adapters)
        validation_result['adapters'] = list(adapters.keys())
        validation_result['properties_per_adapter'] = len(required_properties)

    except Exception as e:
        validation_result['success'] = False
        validation_result['issues'].append(f'Platform adapter validation failed: {e}')

    return validation_result


def run_all_startup_validations() -> dict[str, Any]:
    logger.info('Running startup tool validation...')

    results: dict[str, Any] = {
        'overall_success': True,
        'validations': {
            'respec_ai_tools': validate_respec_ai_tools_at_startup(),
            'external_platform_tools': validate_external_platform_tools(),
            'platform_adapters': validate_platform_adapters(),
        },
        'summary': {'total_issues': 0, 'critical_issues': [], 'warnings': []},
    }

    # Collect all issues
    all_issues = []
    for validation_name, validation_result in results['validations'].items():
        if not validation_result.get('success', True):
            results['overall_success'] = False

        issues = validation_result.get('issues', [])
        for issue in issues:
            issue_with_context = f'[{validation_name}] {issue}'
            all_issues.append(issue_with_context)

            # Categorize issues
            if 'missing' in issue.lower() or 'not registered' in issue.lower():
                results['summary']['critical_issues'].append(issue_with_context)
            else:
                results['summary']['warnings'].append(issue_with_context)

    results['summary']['total_issues'] = len(all_issues)

    # Log results
    if results['overall_success']:
        logger.info('✅ All startup validations passed')
    else:
        logger.error(f'❌ Startup validation failed with {len(all_issues)} issues')
        for issue in all_issues:
            logger.error(f'  - {issue}')

    return results


def ensure_startup_validation_passes() -> None:
    results = run_all_startup_validations()

    if not results['overall_success']:
        critical_issues = results['summary']['critical_issues']
        if critical_issues:
            raise StartupValidationError(
                'Critical startup validation failures:\n' + '\n'.join(f'  • {issue}' for issue in critical_issues)
            )

        warnings = results['summary']['warnings']
        if warnings:
            logger.warning('Startup validation warnings (non-critical):')
            for warning in warnings:
                logger.warning(f'  • {warning}')
