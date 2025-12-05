from unittest.mock import MagicMock

import pytest
from fastmcp.exceptions import ResourceError, ToolError
from pytest_mock import MockerFixture

from src.mcp.tools.roadmap_tools import RoadmapTools
from src.models.enums import RoadmapStatus
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec
from src.utils.state_manager import StateManager


@pytest.fixture
def project_path() -> str:
    return '/tmp/test-project'


def create_test_roadmap_markdown(project_name: str) -> str:
    return f"""# Project Roadmap: {project_name}

## Project Details
- **Project Goal**: Build and deploy {project_name}
- **Total Duration**: 6 months
- **Team Size**: 5 developers
- **Budget**: $100,000

## Specifications


## Risk Assessment
- **Critical Path Analysis**: Critical path analysis pending
- **Key Risks**: Standard development risks
- **Mitigation Plans**: Standard mitigation strategies
- **Buffer Time**: 2 weeks

## Resource Planning
- **Development Resources**: 5 developers, 1 PM
- **Infrastructure Requirements**: AWS cloud infrastructure
- **External Dependencies**: None identified
- **Quality Assurance Plan**: Automated testing and manual QA

## Success Metrics
- **Technical Milestones**: Alpha, Beta, Production release
- **Business Milestones**: User adoption targets
- **Quality Gates**: Code review, testing, security review
- **Performance Targets**: Sub-2s response times

## Metadata
- **Status**: draft
- **Created**: 2024-01-01
- **Last Updated**: 2024-01-01
- **Spec Count**: 0
"""


class TestRoadmapTools:
    @pytest.fixture
    def mock_state_manager(self, mocker: MockerFixture) -> MagicMock:
        return mocker.Mock(spec=StateManager)

    @pytest.fixture
    def roadmap_tools(self, mock_state_manager: MagicMock) -> RoadmapTools:
        return RoadmapTools(mock_state_manager)

    @pytest.fixture
    def valid_spec_markdown(self) -> str:
        return """# Technical Specification: User Authentication

## Overview

### Objectives
Implement secure user authentication system

### Scope
Login, logout, session management

### Dependencies
Database setup, encryption library

### Deliverables
User login/logout endpoints, session management middleware

## Metadata

### Status
draft

### Created
2024-01-15

### Last Updated
2024-01-15

### Owner
Test Team
"""

    @pytest.fixture
    def malformed_spec_markdown(self) -> str:
        return """# Some title
        
This is not properly formatted spec markdown.
Missing required sections and structure.
"""


class TestCreateRoadmap(TestRoadmapTools):
    def test_create_roadmap_returns_success_message(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        mock_state_manager.store_roadmap.return_value = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')

        result = roadmap_tools.create_roadmap('test-project', roadmap_markdown)

        assert isinstance(result, str)
        assert 'Test Roadmap' in result
        assert 'test-project' in result
        assert 'Created roadmap' in result

    def test_create_roadmap_delegates_to_state_manager(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        mock_state_manager.store_roadmap.return_value = 'project-123'
        roadmap_markdown = create_test_roadmap_markdown('My Roadmap')

        roadmap_tools.create_roadmap('project-123', roadmap_markdown)

        mock_state_manager.store_roadmap.assert_called_once()
        call_args = mock_state_manager.store_roadmap.call_args
        assert call_args[0][0] == 'project-123'  # project_name
        assert isinstance(call_args[0][1], Roadmap)  # roadmap instance
        assert call_args[0][1].project_name == 'My Roadmap'

    def test_create_roadmap_raises_error_for_empty_project_name(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        with pytest.raises(ToolError, match='Project name cannot be empty'):
            roadmap_tools.create_roadmap('', 'Test Roadmap')

    def test_create_roadmap_raises_error_for_empty_roadmap_data(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        with pytest.raises(ToolError, match='Roadmap data cannot be empty'):
            roadmap_tools.create_roadmap('test-project', '')

    @pytest.mark.parametrize(
        'project_name,roadmap_name',
        [
            ('simple-project', 'Simple Roadmap'),
            ('project-with-special-chars!@#', 'Roadmap with émojis 🚀'),
            ('very-long-project-id-' + 'x' * 50, 'Long name test'),
        ],
    )
    def test_create_roadmap_handles_various_inputs(
        self,
        roadmap_tools: RoadmapTools,
        mock_state_manager: MagicMock,
        project_name: str,
        roadmap_name: str,
    ) -> None:
        mock_state_manager.store_roadmap.return_value = project_name
        roadmap_markdown = create_test_roadmap_markdown(roadmap_name)

        result = roadmap_tools.create_roadmap(project_name, roadmap_markdown)

        assert isinstance(result, str)
        assert roadmap_name in result


class TestGetRoadmap(TestRoadmapTools):
    def test_get_roadmap_returns_success_with_spec_count(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        mock_specs = [
            TechnicalSpec(
                phase_name='spec1',
                objectives='Test objectives 1',
                scope='Test scope 1',
                dependencies='Test deps 1',
                deliverables='Test deliverables 1',
            ),
            TechnicalSpec(
                phase_name='spec2',
                objectives='Test objectives 2',
                scope='Test scope 2',
                dependencies='Test deps 2',
                deliverables='Test deliverables 2',
            ),
            TechnicalSpec(
                phase_name='spec3',
                objectives='Test objectives 3',
                scope='Test scope 3',
                dependencies='Test deps 3',
                deliverables='Test deliverables 3',
            ),
        ]

        mock_roadmap = Roadmap(
            project_name='Test Roadmap',
            project_goal='Test goal',
            total_duration='6 months',
            team_size='5 developers',
            roadmap_budget='$100k',
            critical_path_analysis='Test analysis',
            key_risks='Test risks',
            mitigation_plans='Test plans',
            buffer_time='1 week',
            development_resources='Test resources',
            infrastructure_requirements='Test infrastructure',
            external_dependencies='Test dependencies',
            quality_assurance_plan='Test QA',
            technical_milestones='Test milestones',
            business_milestones='Test business',
            quality_gates='Test gates',
            performance_targets='Test performance',
            roadmap_status=RoadmapStatus.DRAFT,
        )
        mock_state_manager.get_roadmap.return_value = mock_roadmap
        mock_state_manager.get_roadmap_specs.return_value = mock_specs

        result = roadmap_tools.get_roadmap('test-project')

        assert isinstance(result, str)
        assert 'Test Roadmap' in result
        # Check for full TechnicalSpec content (not summary list)
        assert '# Technical Specification: spec1' in result
        assert '# Technical Specification: spec2' in result
        assert '# Technical Specification: spec3' in result

    def test_get_roadmap_raises_error_when_not_found(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        mock_state_manager.get_roadmap.side_effect = Exception('Not found')

        with pytest.raises(ResourceError, match='Roadmap not found for project non-existent-project'):
            roadmap_tools.get_roadmap('non-existent-project')

    def test_get_roadmap_handles_empty_roadmap(
        self, roadmap_tools: RoadmapTools, mock_state_manager: MagicMock
    ) -> None:
        mock_roadmap = Roadmap(
            project_name='Empty Roadmap',
            project_goal='Test goal',
            total_duration='6 months',
            team_size='5 developers',
            roadmap_budget='$100k',
            critical_path_analysis='Test analysis',
            key_risks='Test risks',
            mitigation_plans='Test plans',
            buffer_time='1 week',
            development_resources='Test resources',
            infrastructure_requirements='Test infrastructure',
            external_dependencies='Test dependencies',
            quality_assurance_plan='Test QA',
            technical_milestones='Test milestones',
            business_milestones='Test business',
            quality_gates='Test gates',
            performance_targets='Test performance',
            roadmap_status=RoadmapStatus.DRAFT,
        )
        mock_state_manager.get_roadmap.return_value = mock_roadmap
        mock_state_manager.get_roadmap_specs.return_value = []

        result = roadmap_tools.get_roadmap('empty-project')

        assert isinstance(result, str)
        # For empty specs list, no TechnicalSpec sections should be present
        assert '# Technical Specification:' not in result
        # Metadata should still be present
        assert '## Metadata' in result
        assert '### Spec Count\n0' in result
