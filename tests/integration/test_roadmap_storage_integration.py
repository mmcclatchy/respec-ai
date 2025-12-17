import pytest

from src.mcp.tools.roadmap_tools import RoadmapTools
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def plan_name() -> str:
    return 'test-project'


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager()


@pytest.fixture
def roadmap_tools(state_manager: InMemoryStateManager) -> RoadmapTools:
    return RoadmapTools(state_manager)


@pytest.fixture
def sample_roadmap_markdown_with_phases() -> str:
    return """# Plan Roadmap: RAG Best Practices POC

## Plan Details

### Plan Goal
Create a proof-of-concept intelligent knowledge management system

### Total Duration
16 hours

### Team Size
1 developer

### Budget
Not specified

## Risk Assessment

### Critical Path Analysis
Neo4j setup is on critical path

### Key Risks
Technical complexity with vector similarity

### Mitigation Plans
Start with simple embeddings

### Buffer Time
2 hours

## Resource Planning

### Development Resources
1 developer full-time

### Infrastructure Requirements
Neo4j database with vector support

### External Dependencies
Exa API for web searches

### Quality Assurance Plan
Unit tests for each phase

## Success Metrics

### Technical Milestones
Working vector storage and retrieval

### Business Milestones
Validate caching strategy

### Quality Gates
All tests pass

### Performance Targets
Sub-second query response

## Metadata

### Status
draft

### Phase Count
3

# Phase: phase-1-neo4j-setup

## Overview

### Objectives
Set up Neo4j database with vector extensions

### Scope
Database installation and configuration only

### Dependencies
None

### Deliverables
Working Neo4j instance with vector support

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Phase: phase-2-embedding-pipeline

## Overview

### Objectives
Create embedding generation and storage pipeline

### Scope
Best practice content embedding and storage

### Dependencies
Phase 1 complete

### Deliverables
Working embedding storage system

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Phase: phase-3-query-system

## Overview

### Objectives
Implement vector similarity search

### Scope
Query interface with similarity ranking

### Dependencies
Phase 2 complete

### Deliverables
Working query system with results

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""


class TestRoadmapStorageIntegration:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_roadmap_with_phases(
        self, roadmap_tools: RoadmapTools, plan_name: str, sample_roadmap_markdown_with_phases: str
    ) -> None:
        # Store roadmap
        result = await roadmap_tools.store(plan_name, sample_roadmap_markdown_with_phases)

        assert result.id == plan_name

        # Retrieve roadmap
        response = await roadmap_tools.get(key=plan_name)
        retrieved_markdown = response.message

        assert isinstance(retrieved_markdown, str)
        assert '# Plan Roadmap: RAG Best Practices POC' in retrieved_markdown
        assert 'Create a proof-of-concept intelligent knowledge management system' in retrieved_markdown

        # Verify full Phase content is present
        assert '# Phase: phase-1-neo4j-setup' in retrieved_markdown
        assert '# Phase: phase-2-embedding-pipeline' in retrieved_markdown
        assert '# Phase: phase-3-query-system' in retrieved_markdown

        # Verify Phase details are preserved
        assert 'Set up Neo4j database with vector extensions' in retrieved_markdown
        assert 'Create embedding generation and storage pipeline' in retrieved_markdown
        assert 'Implement vector similarity search' in retrieved_markdown

    @pytest.mark.asyncio
    async def test_round_trip_preserves_all_content(
        self, roadmap_tools: RoadmapTools, plan_name: str, sample_roadmap_markdown_with_phases: str
    ) -> None:
        # Store original
        await roadmap_tools.store(plan_name, sample_roadmap_markdown_with_phases)

        # Retrieve
        response = await roadmap_tools.get(key=plan_name)
        retrieved_markdown = response.message

        # Parse retrieved markdown like store does
        phase_blocks = retrieved_markdown.split('# Phase:')
        assert len(phase_blocks) == 4  # Roadmap metadata + 3 phases

        # Store retrieved markdown again (simulating agent workflow)
        result = await roadmap_tools.store(plan_name, retrieved_markdown)
        assert result.id == plan_name

        # Retrieve again
        second_response = await roadmap_tools.get(key=plan_name)
        second_retrieval = second_response.message

        # Verify content still matches
        assert '# Plan Roadmap: RAG Best Practices POC' in second_retrieval
        assert '# Phase: phase-1-neo4j-setup' in second_retrieval
        assert '# Phase: phase-2-embedding-pipeline' in second_retrieval
        assert '# Phase: phase-3-query-system' in second_retrieval

    @pytest.mark.asyncio
    async def test_store_roadmap_with_invalid_title_format(self, roadmap_tools: RoadmapTools, plan_name: str) -> None:
        invalid_markdown = """# Implementation Roadmap: My Plan

## Plan Details

### Plan Goal
Test goal

### Total Duration
8 weeks

### Team Size
4 developers

### Budget
$100,000

## Risk Assessment

### Critical Path Analysis
Test

### Key Risks
Test

### Mitigation Plans
Test

### Buffer Time
Test

## Resource Planning

### Development Resources
Test

### Infrastructure Requirements
Test

### External Dependencies
Test

### Quality Assurance Plan
Test

## Success Metrics

### Technical Milestones
Test

### Business Milestones
Test

### Quality Gates
Test

### Performance Targets
Test

## Metadata

### Status
draft

### Phase Count
0
"""

        # Should fail with clear error about title format
        with pytest.raises(Exception) as exc_info:
            await roadmap_tools.store(plan_name, invalid_markdown)

        assert 'title' in str(exc_info.value).lower() or 'roadmap' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_roadmap(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(Exception) as exc_info:
            await roadmap_tools.get(key='nonexistent-project')

        assert 'not found' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_store_roadmap_without_phases(self, roadmap_tools: RoadmapTools, plan_name: str) -> None:
        minimal_roadmap = """# Plan Roadmap: Minimal Plan

## Plan Details

### Plan Goal
Test goal

### Total Duration
8 weeks

### Team Size
4 developers

### Budget
$100,000

## Risk Assessment

### Critical Path Analysis
Test

### Key Risks
Test

### Mitigation Plans
Test

### Buffer Time
Test

## Resource Planning

### Development Resources
Test

### Infrastructure Requirements
Test

### External Dependencies
Test

### Quality Assurance Plan
Test

## Success Metrics

### Technical Milestones
Test

### Business Milestones
Test

### Quality Gates
Test

### Performance Targets
Test

## Metadata

### Status
draft

### Phase Count
0
"""

        result = await roadmap_tools.store(plan_name, minimal_roadmap)
        assert result.id == plan_name

        response = await roadmap_tools.get(key=plan_name)
        retrieved = response.message
        assert '# Plan Roadmap: Minimal Plan' in retrieved
        assert '# Phase:' not in retrieved
