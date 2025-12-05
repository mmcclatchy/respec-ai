"""Shared fixtures for model tests.

This module provides dynamic fixture generation to minimize maintenance burden
when models change. The markdown_builder generates valid markdown from model
metadata (HEADER_FIELD_MAPPING) rather than using model output, avoiding
circular testing.
"""

from enum import Enum
from typing import Any, Callable, Type

import pytest
from src.models.base import MCPModel


@pytest.fixture
def markdown_builder() -> Callable:
    """Build minimal valid markdown for any MCPModel dynamically.

    This fixture generates markdown by directly reading model metadata
    (HEADER_FIELD_MAPPING) and constructing markdown strings manually,
    NOT by calling model.build_markdown(). This ensures we're testing
    parse_markdown() against independently-constructed input.

    Benefits:
    - Automatically adapts when fields are added/removed/renamed
    - Zero maintenance when model structure changes
    - Not circular testing (builds from metadata, not model output)
    - Generates realistic domain-appropriate content

    Usage:
        markdown = markdown_builder(TechnicalSpec,
                                   phase_name='Auth System',
                                   objectives='Implement secure login')
        spec = TechnicalSpec.parse_markdown(markdown)

    Args:
        model_class: The MCPModel subclass to generate markdown for
        **field_values: Field values to override defaults. Any field can be
                       overridden. Fields not specified will use sensible
                       default values.

    Returns:
        Markdown string that conforms to the model's expected structure
    """

    def build(model_class: Type[MCPModel], **field_values: Any) -> str:
        title_field = model_class.TITLE_FIELD
        title = field_values.pop(title_field, 'test-project')

        lines = [f'{model_class.TITLE_PATTERN}: {title}']

        current_h2 = None

        for field_name, header_path in sorted(model_class.HEADER_FIELD_MAPPING.items(), key=lambda x: x[1]):
            h2 = header_path[0]
            h3 = header_path[1] if len(header_path) > 1 else None

            if h2 != current_h2:
                lines.append(f'\n## {h2}')
                current_h2 = h2

            if h3:
                if field_name in field_values:
                    value = field_values[field_name]
                    if isinstance(value, Enum):
                        content = value.value
                    else:
                        content = str(value)
                else:
                    content = _generate_realistic_content(field_name)

                lines.append(f'\n### {h3}\n{content}')

        return '\n'.join(lines) + '\n'

    return build


def _generate_realistic_content(field_name: str) -> str:
    """Generate realistic default content for a field.

    Uses domain-appropriate language and realistic values rather than
    generic placeholders like "test string 123".
    """
    realistic_defaults = {
        'objectives': 'Implement core functionality',
        'scope': 'Feature implementation and testing',
        'dependencies': 'External services and libraries',
        'deliverables': 'Working implementation',
        'architecture': 'Microservice architecture',
        'technology_stack': 'Python FastAPI',
        'functional_requirements': 'Core feature requirements',
        'non_functional_requirements': 'Performance and reliability',
        'development_plan': 'Phased implementation',
        'testing_strategy': 'Unit and integration tests',
        'research_requirements': 'Technology evaluation',
        'success_criteria': 'All tests passing',
        'integration_context': 'Service integration',
        'project_goal': 'Deliver project successfully',
        'project_vision': 'Transform user experience',
        'project_mission': 'Build quality solution',
        'project_timeline': '6 months',
        'project_budget': '$100,000',
        'total_duration': '6 months',
        'team_size': '4 developers',
        'roadmap_budget': '$100,000',
        'primary_objectives': 'Achieve business goals',
        'success_metrics': 'Key performance indicators',
        'key_performance_indicators': 'Measurable outcomes',
        'included_features': 'Core capabilities',
        'excluded_features': 'Out of scope items',
        'project_assumptions': 'Planning assumptions',
        'project_constraints': 'Budget and timeline limits',
        'project_sponsor': 'Executive sponsor',
        'key_stakeholders': 'Project team',
        'end_users': 'Target users',
        'work_breakdown': 'Project phases',
        'phases_overview': 'Implementation stages',
        'project_dependencies': 'External dependencies',
        'team_structure': 'Team composition',
        'technology_requirements': 'Technical stack',
        'infrastructure_needs': 'Infrastructure requirements',
        'identified_risks': 'Project risks',
        'mitigation_strategies': 'Risk mitigation',
        'contingency_plans': 'Backup plans',
        'quality_standards': 'Quality requirements',
        'acceptance_criteria': 'Acceptance criteria',
        'reporting_structure': 'Status reporting',
        'meeting_schedule': 'Regular meetings',
        'documentation_standards': 'Documentation requirements',
        'primary_language': 'Python',
        'framework': 'FastAPI',
        'database': 'PostgreSQL',
        'development_environment': 'Docker-based development',
        'database_schema': 'Database structure',
        'api_architecture': 'RESTful API',
        'frontend_architecture': 'React frontend',
        'core_features': 'Core functionality',
        'integration_points': 'External integrations',
        'code_standards': 'Coding standards',
        'performance_requirements': 'Performance targets',
        'security_implementation': 'Security measures',
        'critical_path_analysis': 'Critical path identification',
        'key_risks': 'Key project risks',
        'mitigation_plans': 'Risk mitigation plans',
        'buffer_time': '2 weeks',
        'development_resources': 'Development team',
        'infrastructure_requirements': 'Infrastructure needs',
        'external_dependencies': 'External dependencies',
        'quality_assurance_plan': 'QA approach',
        'technical_milestones': 'Technical goals',
        'business_milestones': 'Business objectives',
        'quality_gates': 'Quality checkpoints',
        'performance_targets': 'Performance goals',
        'feature_name': 'Feature name',
        'feature_description': 'Feature description',
        'business_value': 'Business value',
        'user_story': 'User story',
        'implementation_approach': 'Implementation strategy',
        'data_models': 'Data structures',
        'api_endpoints': 'API endpoints',
        'ui_components': 'UI components',
        'test_cases': 'Test scenarios',
        'edge_cases': 'Edge cases',
        'iteration': '0',
        'version': '1',
        'effort_estimate': '5 days',
        'priority': 'high',
        'spec_count': '1',
        'roadmap_status': 'draft',
        'spec_status': 'draft',
        'project_status': 'draft',
        'build_status': 'planning',
        'requirements_status': 'draft',
    }

    content = realistic_defaults.get(field_name)
    if content:
        return content

    readable_name = field_name.replace('_', ' ').title()
    return f'Test {readable_name}'
