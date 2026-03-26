"""Shared fixtures for integration tests."""

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

    Usage:
        markdown = markdown_builder(Phase,
                                   phase_name='Auth System',
                                   objectives='Implement secure login')
        phase = Phase.parse_markdown(markdown)

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

            if field_name in field_values:
                value = field_values[field_name]
                if isinstance(value, Enum):
                    content = value.value
                else:
                    content = str(value)
            else:
                content = _generate_realistic_content(field_name)

            if h3:
                lines.append(f'\n### {h3}\n{content}')
            else:
                lines.append(f'\n{content}')

        return '\n'.join(lines) + '\n'

    return build


def _generate_realistic_content(field_name: str) -> str:
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
        'total_duration': '6 months',
        'team_size': '4 developers',
        'roadmap_budget': '$100,000',
        'acceptance_criteria': 'Acceptance criteria',
        'executive_summary': '### Vision\nTransform user experience\n\n### Mission\nBuild quality solution\n\n### Timeline\n6 months\n\n### Budget\n$100,000',
        'business_objectives': '### Primary Objectives\nAchieve business goals\n\n### Success Metrics\nKey performance indicators\n\n### Key Performance Indicators\nMeasurable outcomes',
        'plan_scope': '### Included Features\nCore capabilities\n\n### Anti-Requirements\nOut of scope items\n\n### Assumptions\nPlanning assumptions\n\n### Constraints\nBudget and timeline limits',
        'stakeholders': '### Plan Sponsor\nExecutive sponsor\n\n### Key Stakeholders\nProject team\n\n### End Users\nTarget users',
        'architecture_direction': '### Architecture Overview\nMicroservice architecture\n\n### Data Flow\nAPI-driven data flow',
        'technology_decisions': '### Chosen Technologies\nPython FastAPI\n\n### Rejected Technologies\nNone rejected',
        'plan_structure': '### Work Breakdown\nProject phases\n\n### Phases Overview\nImplementation stages\n\n### Dependencies\nExternal dependencies',
        'resource_requirements': '### Team Structure\nTeam composition\n\n### Technology Requirements\nTechnical stack\n\n### Infrastructure Needs\nInfrastructure requirements',
        'risk_management': '### Identified Risks\nProject risks\n\n### Mitigation Strategies\nRisk mitigation\n\n### Contingency Plans\nBackup plans',
        'quality_assurance': '### Quality Bar\nQuality requirements\n\n### Testing Strategy\nUnit and integration tests\n\n### Acceptance Criteria\nAcceptance criteria',
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
        'sequence': '1',
        'effort_estimate': '5 days',
        'priority': 'high',
        'phase_count': '1',
        'roadmap_status': 'draft',
        'phase_status': 'draft',
        'plan_status': 'draft',
        'build_status': 'planning',
        'requirements_status': 'draft',
    }

    content = realistic_defaults.get(field_name)
    if content:
        return content

    readable_name = field_name.replace('_', ' ').title()
    return f'Test {readable_name}'
