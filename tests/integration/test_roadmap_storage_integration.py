import pytest

from services.mcp.tools.roadmap_tools import RoadmapTools
from services.utils.state_manager import InMemoryStateManager


@pytest.fixture
def project_name() -> str:
    return 'test-project'


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager()


@pytest.fixture
def roadmap_tools(state_manager: InMemoryStateManager) -> RoadmapTools:
    return RoadmapTools(state_manager)


@pytest.fixture
def sample_roadmap_markdown_with_specs() -> str:
    return """# Project Roadmap: RAG Best Practices POC

## Project Details

### Project Goal
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

### Spec Count
3

# Technical Specification: Phase 1 - Neo4j Setup

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

# Technical Specification: Phase 2 - Embedding Pipeline

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

# Technical Specification: Phase 3 - Query System

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
    def test_store_and_retrieve_roadmap_with_specs(
        self, roadmap_tools: RoadmapTools, project_name: str, sample_roadmap_markdown_with_specs: str
    ) -> None:
        # Store roadmap
        result = roadmap_tools.create_roadmap(project_name, sample_roadmap_markdown_with_specs)

        assert 'Created roadmap' in result
        assert project_name in result
        assert '3 specs' in result

        # Retrieve roadmap
        retrieved_markdown = roadmap_tools.get_roadmap(project_name)

        assert isinstance(retrieved_markdown, str)
        assert '# Project Roadmap: RAG Best Practices POC' in retrieved_markdown
        assert 'Create a proof-of-concept intelligent knowledge management system' in retrieved_markdown

        # Verify full TechnicalSpec content is present
        assert '# Technical Specification: Phase 1 - Neo4j Setup' in retrieved_markdown
        assert '# Technical Specification: Phase 2 - Embedding Pipeline' in retrieved_markdown
        assert '# Technical Specification: Phase 3 - Query System' in retrieved_markdown

        # Verify TechnicalSpec details are preserved
        assert 'Set up Neo4j database with vector extensions' in retrieved_markdown
        assert 'Create embedding generation and storage pipeline' in retrieved_markdown
        assert 'Implement vector similarity search' in retrieved_markdown

    def test_round_trip_preserves_all_content(
        self, roadmap_tools: RoadmapTools, project_name: str, sample_roadmap_markdown_with_specs: str
    ) -> None:
        # Store original
        roadmap_tools.create_roadmap(project_name, sample_roadmap_markdown_with_specs)

        # Retrieve
        retrieved_markdown = roadmap_tools.get_roadmap(project_name)

        # Parse retrieved markdown like create_roadmap does
        spec_blocks = retrieved_markdown.split('# Technical Specification:')
        assert len(spec_blocks) == 4  # Roadmap metadata + 3 specs

        # Store retrieved markdown again (simulating agent workflow)
        result = roadmap_tools.create_roadmap(project_name, retrieved_markdown)
        assert 'Created roadmap' in result

        # Retrieve again
        second_retrieval = roadmap_tools.get_roadmap(project_name)

        # Verify content still matches
        assert '# Project Roadmap: RAG Best Practices POC' in second_retrieval
        assert '# Technical Specification: Phase 1 - Neo4j Setup' in second_retrieval
        assert '# Technical Specification: Phase 2 - Embedding Pipeline' in second_retrieval
        assert '# Technical Specification: Phase 3 - Query System' in second_retrieval

    def test_create_roadmap_with_invalid_title_format(self, roadmap_tools: RoadmapTools, project_name: str) -> None:
        invalid_markdown = """# Implementation Roadmap: My Project

## Project Details

### Project Goal
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

### Spec Count
0
"""

        # Should fail with clear error about title format
        with pytest.raises(Exception) as exc_info:
            roadmap_tools.create_roadmap(project_name, invalid_markdown)

        assert 'title' in str(exc_info.value).lower() or 'roadmap' in str(exc_info.value).lower()

    def test_retrieve_nonexistent_roadmap(self, roadmap_tools: RoadmapTools) -> None:
        with pytest.raises(Exception) as exc_info:
            roadmap_tools.get_roadmap('nonexistent-project')

        assert 'not found' in str(exc_info.value).lower()

    def test_store_roadmap_without_specs(self, roadmap_tools: RoadmapTools, project_name: str) -> None:
        minimal_roadmap = """# Project Roadmap: Minimal Project

## Project Details

### Project Goal
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

### Spec Count
0
"""

        result = roadmap_tools.create_roadmap(project_name, minimal_roadmap)
        assert 'Created roadmap' in result
        assert '0 specs' in result

        retrieved = roadmap_tools.get_roadmap(project_name)
        assert '# Project Roadmap: Minimal Project' in retrieved
        assert '# Technical Specification:' not in retrieved

    def test_roadmap_refinement_cleans_orphaned_specs(
        self, roadmap_tools: RoadmapTools, project_name: str, state_manager: InMemoryStateManager
    ) -> None:
        # Create initial roadmap with 3 phases
        roadmap_v1_markdown = """# Project Roadmap: Test Project

## Project Details

### Project Goal
Test goal for refinement

### Total Duration
8 weeks

### Team Size
4 developers

### Budget
$100,000

## Risk Assessment

### Critical Path Analysis
Test analysis

### Key Risks
Test risks

### Mitigation Plans
Test mitigation

### Buffer Time
1 week

## Resource Planning

### Development Resources
4 developers

### Infrastructure Requirements
Cloud hosting

### External Dependencies
None

### Quality Assurance Plan
Automated testing

## Success Metrics

### Technical Milestones
MVP delivery

### Business Milestones
User acceptance

### Quality Gates
All tests pass

### Performance Targets
Fast response

## Metadata

### Status
draft

### Spec Count
3

# Technical Specification: Phase 1 - Setup

## Overview

### Objectives
Setup infrastructure

### Scope
Infrastructure setup only

### Dependencies
None

### Deliverables
Working infrastructure

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Technical Specification: Phase 2 - Development

## Overview

### Objectives
Build features

### Scope
Core feature development

### Dependencies
Phase 1 complete

### Deliverables
Working features

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Technical Specification: Phase 3 - Testing

## Overview

### Objectives
Test system

### Scope
Full system testing

### Dependencies
Phase 2 complete

### Deliverables
Test results

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""

        roadmap_tools.create_roadmap(project_name, roadmap_v1_markdown)

        # Verify 3 specs stored
        specs_v1 = state_manager.list_specs(project_name)
        assert len(specs_v1) == 3
        assert 'Phase 1 - Setup' in specs_v1
        assert 'Phase 2 - Development' in specs_v1
        assert 'Phase 3 - Testing' in specs_v1

        # Refine roadmap: Change phase 2 and 3 names
        roadmap_v2_markdown = """# Project Roadmap: Test Project

## Project Details

### Project Goal
Test goal for refinement

### Total Duration
8 weeks

### Team Size
4 developers

### Budget
$100,000

## Risk Assessment

### Critical Path Analysis
Test analysis

### Key Risks
Test risks

### Mitigation Plans
Test mitigation

### Buffer Time
1 week

## Resource Planning

### Development Resources
4 developers

### Infrastructure Requirements
Cloud hosting

### External Dependencies
None

### Quality Assurance Plan
Automated testing

## Success Metrics

### Technical Milestones
MVP delivery

### Business Milestones
User acceptance

### Quality Gates
All tests pass

### Performance Targets
Fast response

## Metadata

### Status
draft

### Spec Count
3

# Technical Specification: Phase 1 - Setup

## Overview

### Objectives
Setup infrastructure (unchanged)

### Scope
Infrastructure setup only

### Dependencies
None

### Deliverables
Working infrastructure

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Technical Specification: Phase 2 - Implementation

## Overview

### Objectives
Implement features (RENAMED)

### Scope
Core feature implementation

### Dependencies
Phase 1 complete

### Deliverables
Implemented features

## Metadata

### Iteration
0

### Version
1

### Status
draft

# Technical Specification: Phase 3 - Quality Assurance

## Overview

### Objectives
QA testing (RENAMED)

### Scope
Comprehensive QA

### Dependencies
Phase 2 complete

### Deliverables
QA report

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""

        roadmap_tools.create_roadmap(project_name, roadmap_v2_markdown)

        # Verify orphaned specs deleted, new specs stored
        specs_v2 = state_manager.list_specs(project_name)
        assert len(specs_v2) == 3
        assert 'Phase 1 - Setup' in specs_v2
        assert 'Phase 2 - Implementation' in specs_v2
        assert 'Phase 3 - Quality Assurance' in specs_v2

        # Verify old specs removed
        assert 'Phase 2 - Development' not in specs_v2
        assert 'Phase 3 - Testing' not in specs_v2
