import pytest
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.roadmap_tools import RoadmapTools
from src.models.phase import Phase
from src.models.roadmap import Roadmap
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager()


@pytest.fixture
def roadmap_tools(state_manager: InMemoryStateManager) -> RoadmapTools:
    return RoadmapTools(state_manager)


def create_test_roadmap_markdown(plan_name: str) -> str:
    return f"""# Plan Roadmap: {plan_name}

## Plan Details

### Plan Goal
Build and deploy {plan_name}

### Total Duration
6 months

### Team Size
5 developers

### Budget
$100,000

## Specifications


## Risk Assessment

### Critical Path Analysis
Critical path analysis pending

### Key Risks
Standard development risks

### Mitigation Plans
Standard mitigation strategies

### Buffer Time
2 weeks

## Resource Planning

### Development Resources
5 developers, 1 PM

### Infrastructure Requirements
AWS cloud infrastructure

### External Dependencies
None identified

### Quality Assurance Plan
Automated testing and manual QA

## Success Metrics

### Technical Milestones
Alpha, Beta, Production release

### Business Milestones
User adoption targets

### Quality Gates
Code review, testing, security review

### Performance Targets
Sub-2s response times

## Metadata

### Status
draft

### Created
2024-01-01

### Last Updated
2024-01-01

### Phase Count
0
"""


def create_test_phase_markdown(phase_name: str) -> str:
    return f"""# Phase: {phase_name}

## Overview

### Objectives
Implement {phase_name} functionality

### Scope
Core {phase_name} features

### Dependencies
None

### Deliverables
Working {phase_name} implementation

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


class TestRoadmapToolsStore:
    @pytest.mark.asyncio
    async def test_store_creates_roadmap(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')

        response = await roadmap_tools.store(key, roadmap_markdown)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert response.id == key

        assert key in state_manager._roadmaps
        stored_roadmap = state_manager._roadmaps[key]
        assert isinstance(stored_roadmap, Roadmap)
        assert stored_roadmap.plan_name == 'Test Roadmap'

    @pytest.mark.asyncio
    async def test_store_validates_empty_key(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await roadmap_tools.store('', 'some content')

    @pytest.mark.asyncio
    async def test_store_validates_empty_content(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await roadmap_tools.store('test-project', '')

    @pytest.mark.asyncio
    async def test_store_handles_roadmap_with_phases(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')
        phase1_markdown = create_test_phase_markdown('authentication')
        phase2_markdown = create_test_phase_markdown('authorization')

        combined_markdown = roadmap_markdown + '\n' + phase1_markdown + '\n' + phase2_markdown

        response = await roadmap_tools.store(key, combined_markdown)

        assert isinstance(response, MCPResponse)
        assert response.id == key

        assert key in state_manager._roadmaps
        assert key in state_manager._phases
        assert len(state_manager._phases[key]) == 2

    @pytest.mark.parametrize(
        'key,roadmap_name',
        [
            ('simple-project', 'Simple Roadmap'),
            ('project-with-special-chars', 'Roadmap with émojis 🚀'),
            ('very-long-project-id-' + 'x' * 50, 'Long name test'),
        ],
    )
    @pytest.mark.asyncio
    async def test_store_handles_various_inputs(
        self,
        roadmap_tools: RoadmapTools,
        state_manager: InMemoryStateManager,
        key: str,
        roadmap_name: str,
    ) -> None:
        roadmap_markdown = create_test_roadmap_markdown(roadmap_name)

        response = await roadmap_tools.store(key, roadmap_markdown)

        assert isinstance(response, MCPResponse)
        assert key in state_manager._roadmaps
        stored_roadmap = state_manager._roadmaps[key]
        assert stored_roadmap.plan_name == roadmap_name


class TestRoadmapToolsGet:
    @pytest.mark.asyncio
    async def test_get_returns_roadmap_with_phases(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')
        await roadmap_tools.store(key, roadmap_markdown)

        phases = [
            Phase(
                phase_name='phase1',
                objectives='Test objectives 1',
                scope='Test scope 1',
                dependencies='Test deps 1',
                deliverables='Test deliverables 1',
            ),
            Phase(
                phase_name='phase2',
                objectives='Test objectives 2',
                scope='Test scope 2',
                dependencies='Test deps 2',
                deliverables='Test deliverables 2',
            ),
        ]

        for phase in phases:
            await state_manager.store_phase(key, phase)

        response = await roadmap_tools.get(key=key)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert response.id == key
        assert 'Test Roadmap' in response.message
        assert '# Phase: phase1' in response.message
        assert '# Phase: phase2' in response.message

    @pytest.mark.asyncio
    async def test_get_raises_error_when_not_found(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(ResourceError, match='Roadmap not found'):
            await roadmap_tools.get(key='non-existent-project')

    @pytest.mark.asyncio
    async def test_get_requires_key(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(ToolError, match='Key is required for roadmaps'):
            await roadmap_tools.get(key=None)

    @pytest.mark.asyncio
    async def test_get_rejects_loop_id(self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')
        await roadmap_tools.store(key, roadmap_markdown)

        with pytest.raises(ToolError, match='Roadmaps do not support loop-based retrieval'):
            await roadmap_tools.get(key=key, loop_id='a1b2c3d4')

    @pytest.mark.asyncio
    async def test_get_handles_empty_phases(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'empty-project'
        roadmap_markdown = create_test_roadmap_markdown('Empty Roadmap')
        await roadmap_tools.store(key, roadmap_markdown)

        response = await roadmap_tools.get(key=key)

        assert isinstance(response, MCPResponse)
        assert '# Phase:' not in response.message
        assert '## Metadata' in response.message


class TestRoadmapToolsList:
    @pytest.mark.asyncio
    async def test_list_returns_not_implemented(self, roadmap_tools: RoadmapTools) -> None:
        response = await roadmap_tools.list()

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert 'not yet implemented' in response.message.lower()


class TestRoadmapToolsUpdate:
    @pytest.mark.asyncio
    async def test_update_delegates_to_store(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Original Roadmap')
        await roadmap_tools.store(key, roadmap_markdown)

        updated_markdown = create_test_roadmap_markdown('Updated Roadmap')
        response = await roadmap_tools.update(key, updated_markdown)

        assert isinstance(response, MCPResponse)
        assert response.id == key

        stored_roadmap = state_manager._roadmaps[key]
        assert stored_roadmap.plan_name == 'Updated Roadmap'


class TestRoadmapToolsDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_not_implemented(self, roadmap_tools: RoadmapTools) -> None:
        response = await roadmap_tools.delete('test-project')

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert 'not yet implemented' in response.message.lower()


class TestRoadmapToolsLinkLoop:
    @pytest.mark.asyncio
    async def test_link_loop_raises_error(
        self, roadmap_tools: RoadmapTools, state_manager: InMemoryStateManager
    ) -> None:
        key = 'test-project'
        roadmap_markdown = create_test_roadmap_markdown('Test Roadmap')
        await roadmap_tools.store(key, roadmap_markdown)

        with pytest.raises(ToolError, match='Roadmaps do not support loop linking'):
            await roadmap_tools.link_loop('a1b2c3d4', key)
