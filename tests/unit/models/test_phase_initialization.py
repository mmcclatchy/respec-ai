import pytest

from src.models.enums import PhaseStatus
from src.models.phase import Phase


@pytest.fixture
def sample_initial_phase_markdown() -> str:
    return """# Phase: user-authentication-system

## Overview

### Objectives
Implement secure user login and registration

### Scope
Login, logout, password reset functionality

### Dependencies
Database, encryption library

### Deliverables
Working authentication system

## Metadata

### Status
draft

"""


class TestInitialSpecParsing:
    def test_parse_markdown_extracts_basic_fields(self, sample_initial_phase_markdown: str) -> None:
        phase = Phase.parse_markdown(sample_initial_phase_markdown)

        assert phase.phase_name == 'user-authentication-system'
        assert phase.objectives == 'Implement secure user login and registration'
        assert phase.scope == 'Login, logout, password reset functionality'
        assert phase.dependencies == 'Database, encryption library'
        assert phase.deliverables == 'Working authentication system'
        assert phase.phase_status == PhaseStatus.DRAFT

    def test_initial_phase_generates_8_char_id(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

        assert len(phase.id) == 8
        assert phase.id.isalnum()

    def test_build_markdown_creates_initial_phase_format(self) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
            deliverables='Test deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

        markdown = phase.build_markdown()

        assert '# Phase: test-phase' in markdown
        assert '### Objectives\nTest objectives' in markdown
        assert '### Scope\nTest scope' in markdown
        assert '### Dependencies\nTest dependencies' in markdown
        assert '### Deliverables\nTest deliverables' in markdown
        assert '### Status\ndraft' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_initial_phase_markdown: str) -> None:
        original_phase = Phase.parse_markdown(sample_initial_phase_markdown)

        rebuilt_markdown = original_phase.build_markdown()

        reparsed_phase = Phase.parse_markdown(rebuilt_markdown)

        assert original_phase.phase_name == reparsed_phase.phase_name
        assert original_phase.objectives == reparsed_phase.objectives
        assert original_phase.scope == reparsed_phase.scope
        assert original_phase.dependencies == reparsed_phase.dependencies
        assert original_phase.deliverables == reparsed_phase.deliverables
        assert original_phase.phase_status == reparsed_phase.phase_status


class TestInitialSpecUtilities:
    def test_recursive_traversal_utilities_exist(self) -> None:
        assert hasattr(Phase, '_find_nodes_by_type')
        assert hasattr(Phase, '_extract_text_content')
