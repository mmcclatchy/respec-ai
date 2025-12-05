import pytest
from src.models.enums import SpecStatus
from src.models.spec import TechnicalSpec


@pytest.fixture
def sample_initial_spec_markdown() -> str:
    return """# Technical Specification: user-authentication-system

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
    def test_parse_markdown_extracts_basic_fields(self, sample_initial_spec_markdown: str) -> None:
        spec = TechnicalSpec.parse_markdown(sample_initial_spec_markdown)

        assert spec.phase_name == 'user-authentication-system'
        assert spec.objectives == 'Implement secure user login and registration'
        assert spec.scope == 'Login, logout, password reset functionality'
        assert spec.dependencies == 'Database, encryption library'
        assert spec.deliverables == 'Working authentication system'
        assert spec.spec_status == SpecStatus.DRAFT

    def test_initial_spec_generates_8_char_id(self) -> None:
        spec = TechnicalSpec(
            phase_name='test-spec',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='None',
            deliverables='Test deliverables',
            spec_status=SpecStatus.DRAFT,
        )

        assert len(spec.id) == 8
        assert spec.id.isalnum()

    def test_build_markdown_creates_initial_spec_format(self) -> None:
        spec = TechnicalSpec(
            phase_name='test-spec',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
            deliverables='Test deliverables',
            spec_status=SpecStatus.DRAFT,
        )

        markdown = spec.build_markdown()

        assert '# Technical Specification: test-spec' in markdown
        assert '### Objectives\nTest objectives' in markdown
        assert '### Scope\nTest scope' in markdown
        assert '### Dependencies\nTest dependencies' in markdown
        assert '### Deliverables\nTest deliverables' in markdown
        assert '### Status\ndraft' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_initial_spec_markdown: str) -> None:
        original_spec = TechnicalSpec.parse_markdown(sample_initial_spec_markdown)

        rebuilt_markdown = original_spec.build_markdown()

        reparsed_spec = TechnicalSpec.parse_markdown(rebuilt_markdown)

        assert original_spec.phase_name == reparsed_spec.phase_name
        assert original_spec.objectives == reparsed_spec.objectives
        assert original_spec.scope == reparsed_spec.scope
        assert original_spec.dependencies == reparsed_spec.dependencies
        assert original_spec.deliverables == reparsed_spec.deliverables
        assert original_spec.spec_status == reparsed_spec.spec_status


class TestInitialSpecUtilities:
    def test_recursive_traversal_utilities_exist(self) -> None:
        assert hasattr(TechnicalSpec, '_find_nodes_by_type')
        assert hasattr(TechnicalSpec, '_extract_text_content')
