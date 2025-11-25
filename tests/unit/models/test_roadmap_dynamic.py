import pytest

from services.models.roadmap import Roadmap
from services.models.spec import TechnicalSpec
from services.models.enums import RoadmapStatus, SpecStatus


@pytest.fixture
def sample_dynamic_roadmap_markdown() -> str:
    return """# Project Roadmap: E-commerce Platform

## Project Details

### Project Goal
Build modern e-commerce platform

### Total Duration
12 weeks

### Team Size
6 developers

### Budget
$150,000

## Specifications
- **Spec 1**: User Authentication System
- **Spec 2**: Product Catalog Management
- **Spec 3**: Shopping Cart & Checkout

## Risk Assessment

### Critical Path Analysis
Sequential development phases

### Key Risks
Integration complexity

### Mitigation Plans
Incremental delivery

### Buffer Time
2 weeks

## Resource Planning

### Development Resources
6 developers full-time

### Infrastructure Requirements
Cloud hosting

### External Dependencies
Payment gateway

### Quality Assurance Plan
Automated testing

## Success Metrics

### Technical Milestones
Working MVP

### Business Milestones
User acceptance

### Quality Gates
All tests pass

### Performance Targets
Fast response times

## Metadata

### Status
draft

### Spec Count
3
"""


@pytest.fixture
def sample_specs_list() -> list[TechnicalSpec]:
    return [
        TechnicalSpec(
            phase_name='User Authentication System',
            objectives='Implement secure login',
            scope='Login, logout, registration',
            dependencies='Database',
            deliverables='Auth system',
            spec_status=SpecStatus.DRAFT,
            creation_date='2024-01-01',
            last_updated='2024-01-01',
            spec_owner='Backend Team',
        ),
        TechnicalSpec(
            phase_name='Product Catalog Management',
            objectives='Manage product inventory',
            scope='CRUD operations for products',
            dependencies='Auth system',
            deliverables='Product management',
            spec_status=SpecStatus.DRAFT,
            creation_date='2024-01-01',
            last_updated='2024-01-01',
            spec_owner='Backend Team',
        ),
        TechnicalSpec(
            phase_name='Shopping Cart & Checkout',
            objectives='Enable purchase flow',
            scope='Cart, checkout, payments',
            dependencies='Product catalog',
            deliverables='E-commerce flow',
            spec_status=SpecStatus.DRAFT,
            creation_date='2024-01-01',
            last_updated='2024-01-01',
            spec_owner='Frontend Team',
        ),
    ]


class TestDynamicRoadmapParsing:
    def test_parse_markdown_extracts_project_details(self, sample_dynamic_roadmap_markdown: str) -> None:
        roadmap = Roadmap.parse_markdown(sample_dynamic_roadmap_markdown)

        assert roadmap.project_name == 'E-commerce Platform'
        assert roadmap.project_goal == 'Build modern e-commerce platform'
        assert roadmap.total_duration == '12 weeks'
        assert roadmap.team_size == '6 developers'
        assert roadmap.roadmap_budget == '$150,000'

    def test_parse_markdown_extracts_specs_list(self, sample_dynamic_roadmap_markdown: str) -> None:
        roadmap = Roadmap.parse_markdown(sample_dynamic_roadmap_markdown)

        # Specs are not parsed from markdown - they're managed programmatically
        assert len(roadmap.specs) == 0
        # But spec_count can be parsed from metadata
        assert roadmap.spec_count == 3

    def test_parse_markdown_extracts_metadata(self, sample_dynamic_roadmap_markdown: str) -> None:
        roadmap = Roadmap.parse_markdown(sample_dynamic_roadmap_markdown)

        assert roadmap.roadmap_status == RoadmapStatus.DRAFT
        assert roadmap.spec_count == 3

    def test_roadmap_with_specs_list_field(self, sample_specs_list: list[TechnicalSpec]) -> None:
        roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=sample_specs_list,
            critical_path_analysis='Sequential phases',
            key_risks='Technical complexity',
            mitigation_plans='Incremental delivery',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
            spec_count=3,
        )

        assert len(roadmap.specs) == 3
        assert roadmap.spec_count == 3
        assert all(isinstance(spec, TechnicalSpec) for spec in roadmap.specs)

    def test_build_markdown_creates_dynamic_format(self, sample_specs_list: list[TechnicalSpec]) -> None:
        roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=sample_specs_list,
            critical_path_analysis='Sequential phases',
            key_risks='Technical complexity',
            mitigation_plans='Incremental delivery',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
            spec_count=3,
        )

        markdown = roadmap.build_markdown()

        assert '# Project Roadmap: Test Project' in markdown
        assert '## Project Details' in markdown
        assert '### Project Goal\nTest goal' in markdown
        assert '### Total Duration\n8 weeks' in markdown
        assert '### Team Size\n4 developers' in markdown
        assert '### Budget\n$100,000' in markdown
        assert '## Metadata' in markdown
        assert '### Status\ndraft' in markdown
        assert '### Spec Count\n3' in markdown

        # Verify full TechnicalSpec content is included (not summary list)
        assert '# Technical Specification: User Authentication System' in markdown
        assert '# Technical Specification: Product Catalog Management' in markdown
        assert '# Technical Specification: Shopping Cart & Checkout' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_dynamic_roadmap_markdown: str) -> None:
        original_roadmap = Roadmap.parse_markdown(sample_dynamic_roadmap_markdown)

        rebuilt_markdown = original_roadmap.build_markdown()

        reparsed_roadmap = Roadmap.parse_markdown(rebuilt_markdown)

        assert original_roadmap.project_name == reparsed_roadmap.project_name
        assert original_roadmap.project_goal == reparsed_roadmap.project_goal
        assert original_roadmap.total_duration == reparsed_roadmap.total_duration
        assert original_roadmap.team_size == reparsed_roadmap.team_size
        assert original_roadmap.roadmap_budget == reparsed_roadmap.roadmap_budget
        assert len(original_roadmap.specs) == len(reparsed_roadmap.specs)
        assert original_roadmap.spec_count == reparsed_roadmap.spec_count
        assert original_roadmap.roadmap_status == reparsed_roadmap.roadmap_status

        # Specs lists should both be empty (specs not parsed from markdown)
        assert len(original_roadmap.specs) == len(reparsed_roadmap.specs) == 0


class TestRoadmapRoundTripWithSpecs:
    def test_build_markdown_includes_full_spec_content(self, sample_specs_list: list[TechnicalSpec]) -> None:
        roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=sample_specs_list,
            spec_count=3,
        )

        markdown = roadmap.build_markdown()

        # Should include full TechnicalSpec content, not just names
        assert '# Technical Specification: User Authentication System' in markdown
        assert '## Overview' in markdown
        assert '### Objectives' in markdown
        assert 'Implement secure login' in markdown
        assert '### Scope' in markdown
        assert 'Login, logout, registration' in markdown

    def test_build_markdown_round_trip_with_create_roadmap_parser(self, sample_specs_list: list[TechnicalSpec]) -> None:
        original_roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=sample_specs_list,
            spec_count=3,
        )

        # Build markdown
        markdown = original_roadmap.build_markdown()

        # Parse like create_roadmap does (split on # Technical Specification:)
        spec_blocks = markdown.split('# Technical Specification:')
        roadmap_metadata = spec_blocks[0]

        # Parse roadmap metadata
        reparsed_roadmap = Roadmap.parse_markdown(roadmap_metadata)

        # Parse specs
        for spec_block in spec_blocks[1:]:
            spec_markdown = f'# Technical Specification:{spec_block}'
            spec = TechnicalSpec.parse_markdown(spec_markdown)
            reparsed_roadmap.add_spec(spec)

        # Verify round-trip preserved data
        assert reparsed_roadmap.project_name == original_roadmap.project_name
        assert reparsed_roadmap.project_goal == original_roadmap.project_goal
        assert len(reparsed_roadmap.specs) == len(original_roadmap.specs)

        # Verify spec content preserved
        for orig_spec, reparsed_spec in zip(original_roadmap.specs, reparsed_roadmap.specs):
            assert reparsed_spec.phase_name == orig_spec.phase_name
            assert reparsed_spec.objectives == orig_spec.objectives
            assert reparsed_spec.scope == orig_spec.scope
            assert reparsed_spec.dependencies == orig_spec.dependencies
            assert reparsed_spec.deliverables == orig_spec.deliverables

    def test_sparse_specs_only_include_overview_and_metadata(self) -> None:
        sparse_spec = TechnicalSpec(
            phase_name='Phase 1 - Foundation',
            objectives='Build core infrastructure',
            scope='Database and API setup',
            dependencies='None',
            deliverables='Working backend',
            iteration=0,  # Sparse spec
        )

        roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            specs=[sparse_spec],
            spec_count=1,
        )

        markdown = roadmap.build_markdown()

        # Should include Overview section
        assert '# Technical Specification: Phase 1 - Foundation' in markdown
        assert '## Overview' in markdown
        assert '### Objectives' in markdown
        assert 'Build core infrastructure' in markdown

        # Should include Metadata section
        assert '## Metadata' in markdown
        assert '### Iteration' in markdown
        assert '\n0\n' in markdown

        # Should NOT include System Design or Implementation (not set)
        assert '## System Design' not in markdown
        assert '## Implementation' not in markdown


class TestDynamicRoadmapUtilities:
    def test_recursive_traversal_utilities_exist(self) -> None:
        assert hasattr(Roadmap, '_find_nodes_by_type')
        assert hasattr(Roadmap, '_extract_text_content')

    def test_spec_count_property_matches_specs_length(self, sample_specs_list: list[TechnicalSpec]) -> None:
        roadmap = Roadmap(
            project_name='Test Project',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=sample_specs_list,
            critical_path_analysis='Sequential phases',
            key_risks='Technical complexity',
            mitigation_plans='Incremental delivery',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
            spec_count=len(sample_specs_list),
        )

        assert roadmap.spec_count == len(roadmap.specs)
        assert roadmap.spec_count == 3
