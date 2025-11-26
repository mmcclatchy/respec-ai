"""POC test to verify markdown format preservation in Roadmap model round-trips.

This test demonstrates the issue where bullet list content is stripped during
parse -> build -> reparse cycles.
"""

import pytest

from services.models.roadmap import Roadmap


@pytest.fixture
def roadmap_with_bullet_lists() -> str:
    return """# Project Roadmap: Test Project

## Project Details

### Project Goal
Build a comprehensive test system

### Total Duration
8 weeks

### Team Size
4 developers

### Budget
$100,000

## Specifications
- **Spec 1**: Authentication Module
- **Spec 2**: Data Processing Pipeline

## Risk Assessment

### Critical Path Analysis
Sequential phases with dependencies

### Key Risks
- Risk A: Integration with external APIs may cause delays
- Risk B: Performance issues under high load conditions
- Risk C: Database scaling challenges with large datasets

### Mitigation Plans
- Plan A: Early prototype testing for API integrations
- Plan B: Load testing in staging environment
- Plan C: Implement database sharding strategy

### Buffer Time
2 weeks contingency

## Resource Planning

### Development Resources
4 senior developers full-time

### Infrastructure Requirements
Cloud hosting with auto-scaling

### External Dependencies
Third-party authentication service

### Quality Assurance Plan
Automated testing with CI/CD

## Success Metrics

### Technical Milestones
MVP completion by week 6

### Business Milestones
User acceptance testing passed

### Quality Gates
95% test coverage minimum

### Performance Targets
Response time under 200ms

## Metadata

### Status
draft

### Spec Count
2
"""


@pytest.fixture
def roadmap_with_mixed_content() -> str:
    return """# Project Roadmap: Mixed Content Test

## Project Details

### Project Goal
Test mixed content formats

### Total Duration
6 weeks

### Team Size
3 developers

### Budget
$75,000

## Specifications
- **Spec 1**: Core Module

## Risk Assessment

### Critical Path Analysis
The critical path includes several sequential phases that must be completed in order.

This is a multi-paragraph section with detailed analysis.

### Key Risks
We have identified several key risks:

- Risk 1: Technical complexity in integration
- Risk 2: Timeline constraints
- Risk 3: Resource availability

These risks require careful monitoring.

### Mitigation Plans
Structured approach to risk mitigation

### Buffer Time
1 week

## Resource Planning

### Development Resources
3 developers

### Infrastructure Requirements
Basic cloud setup

### External Dependencies
None

### Quality Assurance Plan
Manual testing

## Success Metrics

### Technical Milestones
Completion

### Business Milestones
Acceptance

### Quality Gates
Tests pass

### Performance Targets
Reasonable speed

## Metadata

### Status
draft

### Spec Count
1
"""


def test_bullet_list_content_preserved_in_key_risks(roadmap_with_bullet_lists: str) -> None:
    # Given: Roadmap markdown with bullet list in Key Risks
    original_markdown = roadmap_with_bullet_lists

    # When: Parse the markdown
    roadmap = Roadmap.parse_markdown(original_markdown)

    # Then: Key Risks should contain the bullet list content
    # Note: This may fail if bullets are stripped to plain text
    assert 'Risk A: Integration with external APIs' in roadmap.key_risks
    assert 'Risk B: Performance issues under high load' in roadmap.key_risks
    assert 'Risk C: Database scaling challenges' in roadmap.key_risks

    # When: Build markdown and reparse
    rebuilt_markdown = roadmap.build_markdown()
    reparsed_roadmap = Roadmap.parse_markdown(rebuilt_markdown)

    # Then: Round-trip should preserve the content
    assert roadmap.key_risks == reparsed_roadmap.key_risks, 'Key Risks content changed during round-trip'


def test_bullet_list_content_preserved_in_mitigation_plans(roadmap_with_bullet_lists: str) -> None:
    # Given: Roadmap markdown with bullet lists
    original_markdown = roadmap_with_bullet_lists

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(original_markdown)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Mitigation Plans content should be preserved
    assert 'Plan A: Early prototype testing' in roadmap.mitigation_plans
    assert 'Plan B: Load testing in staging' in roadmap.mitigation_plans
    assert 'Plan C: Implement database sharding' in roadmap.mitigation_plans

    assert roadmap.mitigation_plans == reparsed.mitigation_plans, 'Mitigation Plans content changed during round-trip'


def test_mixed_content_format_preserved(roadmap_with_mixed_content: str) -> None:
    # Given: Roadmap with mixed content formats
    original_markdown = roadmap_with_mixed_content

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(original_markdown)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Both paragraph and bullet content should be preserved
    # Paragraph content
    assert 'critical path includes several sequential phases' in roadmap.critical_path_analysis
    assert 'multi-paragraph section' in roadmap.critical_path_analysis

    # Bullet list content
    assert 'Risk 1: Technical complexity' in roadmap.key_risks
    assert 'Risk 2: Timeline constraints' in roadmap.key_risks
    assert 'Risk 3: Resource availability' in roadmap.key_risks

    # Additional context text
    assert 'identified several key risks' in roadmap.key_risks or 'require careful monitoring' in roadmap.key_risks

    # Round-trip preservation
    assert roadmap.key_risks == reparsed.key_risks, 'Mixed content changed during round-trip'


def test_plain_text_content_still_works() -> None:
    markdown = """# Project Roadmap: Plain Text Test

## Project Details

### Project Goal
Simple plain text goal

### Total Duration
4 weeks

### Team Size
2 developers

### Budget
$50,000

## Specifications
- **Spec 1**: Module A

## Risk Assessment

### Critical Path Analysis
Plain text analysis without lists

### Key Risks
Plain text risks without bullet points

### Mitigation Plans
Plain text mitigation without lists

### Buffer Time
1 week

## Resource Planning

### Development Resources
2 developers

### Infrastructure Requirements
Simple setup

### External Dependencies
None

### Quality Assurance Plan
Basic testing

## Success Metrics

### Technical Milestones
Done

### Business Milestones
Accepted

### Quality Gates
Passed

### Performance Targets
Fast

## Metadata

### Status
draft

### Spec Count
1
"""

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(markdown)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Plain text should be preserved (this should already work)
    assert roadmap.key_risks == 'Plain text risks without bullet points'
    assert roadmap.key_risks == reparsed.key_risks


def test_character_for_character_round_trip(roadmap_with_bullet_lists: str) -> None:
    # Given: Original markdown with bullet lists
    original_markdown = roadmap_with_bullet_lists

    # When: Parse, build, and parse again
    first_parse = Roadmap.parse_markdown(original_markdown)
    first_build = first_parse.build_markdown()
    second_parse = Roadmap.parse_markdown(first_build)
    second_build = second_parse.build_markdown()

    # Then: Second build should match first build exactly
    # This is the strictest test - markdown should stabilize after first round-trip
    assert first_build == second_build, 'Markdown changed between first and second round-trip'


def test_ordered_lists_preserved() -> None:
    markdown_with_ordered_lists = """# Project Roadmap: Ordered List Test

## Project Details

### Project Goal
Test ordered list preservation

### Total Duration
4 weeks

### Team Size
3 developers

### Budget
$75,000

## Specifications
- **Spec 1**: Core Module

## Risk Assessment

### Critical Path Analysis
Sequential implementation phases

### Key Risks
1. First risk: API integration complexity
2. Second risk: Performance optimization challenges
3. Third risk: Timeline constraints and dependencies

### Mitigation Plans
1. Plan A: Early prototyping for API validation
2. Plan B: Performance benchmarking in staging
3. Plan C: Buffer time allocation for critical paths

### Buffer Time
2 weeks

## Resource Planning

### Development Resources
3 developers

### Infrastructure Requirements
Cloud infrastructure

### External Dependencies
Third-party services

### Quality Assurance Plan
Comprehensive testing

## Success Metrics

### Technical Milestones
Implementation complete

### Business Milestones
Stakeholder approval

### Quality Gates
All tests passing

### Performance Targets
Response time targets

## Metadata

### Status
draft

### Spec Count
1
"""

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(markdown_with_ordered_lists)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Ordered list content should be preserved
    assert (
        '1. First risk: API integration complexity' in roadmap.key_risks
        or 'First risk: API integration complexity' in roadmap.key_risks
    )
    assert (
        '2. Second risk: Performance optimization' in roadmap.key_risks
        or 'Second risk: Performance optimization' in roadmap.key_risks
    )
    assert (
        '3. Third risk: Timeline constraints' in roadmap.key_risks
        or 'Third risk: Timeline constraints' in roadmap.key_risks
    )

    # Mitigation plans should also preserve ordered list content
    assert 'Plan A: Early prototyping' in roadmap.mitigation_plans
    assert 'Plan B: Performance benchmarking' in roadmap.mitigation_plans
    assert 'Plan C: Buffer time allocation' in roadmap.mitigation_plans

    # Round-trip should preserve the content
    assert roadmap.key_risks == reparsed.key_risks, 'Ordered list content changed during round-trip'
    assert roadmap.mitigation_plans == reparsed.mitigation_plans, 'Ordered mitigation plans changed during round-trip'


def test_nested_bullet_lists_preserved() -> None:
    markdown_with_nested_lists = """# Project Roadmap: Nested List Test

## Project Details

### Project Goal
Test nested bullet list preservation

### Total Duration
6 weeks

### Team Size
4 developers

### Budget
$100,000

## Specifications
- **Spec 1**: Multi-tier Module

## Risk Assessment

### Critical Path Analysis
Phased approach with dependencies

### Key Risks
- Major Risk Category A: Technical Challenges
  - Sub-risk A1: API integration complexity
  - Sub-risk A2: Performance bottlenecks
    - Detail: Database query optimization needed
    - Detail: Caching strategy required
- Major Risk Category B: Resource Constraints
  - Sub-risk B1: Team availability
  - Sub-risk B2: Budget limitations

### Mitigation Plans
- Strategy 1: Technical Risk Mitigation
  - Action: Early prototyping
  - Action: Regular performance testing
- Strategy 2: Resource Planning
  - Action: Cross-training team members
  - Action: Flexible timeline adjustments

### Buffer Time
3 weeks

## Resource Planning

### Development Resources
4 developers full-time

### Infrastructure Requirements
Cloud with auto-scaling

### External Dependencies
Third-party APIs

### Quality Assurance Plan
Automated testing suite

## Success Metrics

### Technical Milestones
All phases complete

### Business Milestones
Stakeholder approval achieved

### Quality Gates
Coverage targets met

### Performance Targets
Response time under threshold

## Metadata

### Status
draft

### Spec Count
1
"""

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(markdown_with_nested_lists)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Nested list content should be preserved (both parent and child items)
    # Parent items
    assert 'Major Risk Category A: Technical Challenges' in roadmap.key_risks
    assert 'Major Risk Category B: Resource Constraints' in roadmap.key_risks

    # Child items (first level nesting)
    assert 'Sub-risk A1: API integration' in roadmap.key_risks
    assert 'Sub-risk A2: Performance bottlenecks' in roadmap.key_risks
    assert 'Sub-risk B1: Team availability' in roadmap.key_risks

    # Nested child items (second level nesting)
    assert (
        'Detail: Database query optimization' in roadmap.key_risks or 'Database query optimization' in roadmap.key_risks
    )
    assert 'Detail: Caching strategy' in roadmap.key_risks or 'Caching strategy' in roadmap.key_risks

    # Mitigation plans nested structure
    assert 'Strategy 1: Technical Risk Mitigation' in roadmap.mitigation_plans
    assert 'Action: Early prototyping' in roadmap.mitigation_plans
    assert 'Strategy 2: Resource Planning' in roadmap.mitigation_plans
    assert 'Action: Cross-training' in roadmap.mitigation_plans

    # Round-trip should preserve all nested content
    assert roadmap.key_risks == reparsed.key_risks, 'Nested list content changed during round-trip'
    assert roadmap.mitigation_plans == reparsed.mitigation_plans, 'Nested mitigation plans changed during round-trip'


def test_code_blocks_preserved() -> None:
    markdown_with_code_blocks = """# Project Roadmap: Code Block Test

## Project Details

### Project Goal
Test code block preservation in documentation

### Total Duration
5 weeks

### Team Size
3 developers

### Budget
$80,000

## Specifications
- **Spec 1**: Technical Implementation

## Risk Assessment

### Critical Path Analysis
Implementation involves multiple code examples:

```python
def calculate_risk_score(risks: list[str]) -> float:
    return sum(len(r) for r in risks) / len(risks)
```

This function will need careful testing.

### Key Risks
Technical implementation risks include:

```javascript
const apiClient = {
  timeout: 5000,
  retries: 3
};
```

Configuration must be validated.

### Mitigation Plans
Testing strategy example:

```bash
pytest tests/ --cov=src --cov-report=html
npm run test:integration
```

### Buffer Time
2 weeks

## Resource Planning

### Development Resources
3 developers

### Infrastructure Requirements
Cloud deployment

### External Dependencies
APIs and services

### Quality Assurance Plan
Automated testing

## Success Metrics

### Technical Milestones
Code complete

### Business Milestones
Deployment ready

### Quality Gates
Tests passing

### Performance Targets
Optimized performance

## Metadata

### Status
draft

### Spec Count
1
"""

    # When: Parse and round-trip
    roadmap = Roadmap.parse_markdown(markdown_with_code_blocks)
    rebuilt = roadmap.build_markdown()
    reparsed = Roadmap.parse_markdown(rebuilt)

    # Then: Code blocks should be preserved with content
    # Python code block in Critical Path Analysis
    assert (
        'def calculate_risk_score' in roadmap.critical_path_analysis
        or 'calculate_risk_score' in roadmap.critical_path_analysis
    )
    assert (
        'risks: list[str]' in roadmap.critical_path_analysis
        or 'list[str]' in roadmap.critical_path_analysis
        or 'risks' in roadmap.critical_path_analysis
    )

    # JavaScript code block in Key Risks
    assert 'apiClient' in roadmap.key_risks or 'const apiClient' in roadmap.key_risks
    assert 'timeout: 5000' in roadmap.key_risks or 'timeout' in roadmap.key_risks
    assert 'retries: 3' in roadmap.key_risks or 'retries' in roadmap.key_risks

    # Bash code block in Mitigation Plans
    assert 'pytest' in roadmap.mitigation_plans
    assert 'npm run test' in roadmap.mitigation_plans or 'npm' in roadmap.mitigation_plans

    # Round-trip should preserve code block content
    assert roadmap.critical_path_analysis == reparsed.critical_path_analysis, (
        'Code blocks in critical path changed during round-trip'
    )
    assert roadmap.key_risks == reparsed.key_risks, 'Code blocks in key risks changed during round-trip'
    assert roadmap.mitigation_plans == reparsed.mitigation_plans, (
        'Code blocks in mitigation plans changed during round-trip'
    )
