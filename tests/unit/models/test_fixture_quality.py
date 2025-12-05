"""Meta-tests to validate fixture generation quality.

These tests verify that the markdown_builder fixture produces valid, realistic
markdown that successfully parses into model instances. This prevents circular
testing by ensuring the builder creates independently-constructed markdown.
"""

from typing import Callable, Type

import pytest
from src.models.base import MCPModel
from src.models.build_plan import BuildPlan
from src.models.feature_requirements import FeatureRequirements
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec


@pytest.mark.parametrize(
    'model_class',
    [
        Roadmap,
        TechnicalSpec,
        ProjectPlan,
        BuildPlan,
        FeatureRequirements,
    ],
)
def test_markdown_builder_creates_valid_markdown(markdown_builder: Callable, model_class: Type[MCPModel]) -> None:
    """Verify markdown_builder produces valid markdown for all models.

    This meta-test ensures the builder creates markdown that:
    1. Successfully parses without errors
    2. Populates required fields
    3. Contains realistic content (not circular validation)
    """
    markdown = markdown_builder(model_class)

    instance = model_class.parse_markdown(markdown)

    assert instance.model_dump()


@pytest.mark.parametrize(
    'model_class',
    [
        Roadmap,
        TechnicalSpec,
        ProjectPlan,
        BuildPlan,
        FeatureRequirements,
    ],
)
def test_markdown_builder_respects_field_overrides(markdown_builder: Callable, model_class: Type[MCPModel]) -> None:
    title_field = model_class.TITLE_FIELD

    custom_title = 'custom-test-title'
    markdown = markdown_builder(model_class, **{title_field: custom_title})

    instance = model_class.parse_markdown(markdown)

    assert getattr(instance, title_field) == custom_title


def test_markdown_builder_output_differs_from_build_markdown(markdown_builder: Callable) -> None:
    """Verify builder creates independent markdown, not using model's build_markdown().

    This test prevents circular validation by ensuring the builder constructs
    markdown manually from metadata, not by calling model.build_markdown().
    """
    builder_markdown = markdown_builder(TechnicalSpec)

    instance = TechnicalSpec.parse_markdown(builder_markdown)
    model_markdown = instance.build_markdown()

    assert builder_markdown != model_markdown, (
        'Builder markdown should differ from model-generated markdown to avoid circular testing'
    )


def test_markdown_builder_includes_all_header_mapped_fields(markdown_builder: Callable) -> None:
    markdown = markdown_builder(TechnicalSpec)

    for field_name, (h2, h3) in TechnicalSpec.HEADER_FIELD_MAPPING.items():
        if h3:
            assert f'## {h2}' in markdown, f"Missing H2 header '{h2}' for field '{field_name}'"
            assert f'### {h3}' in markdown, f"Missing H3 header '{h3}' for field '{field_name}'"


def test_markdown_builder_generates_realistic_content(markdown_builder: Callable) -> None:
    markdown = markdown_builder(TechnicalSpec)

    assert 'foo' not in markdown.lower()
    assert 'bar' not in markdown.lower()
    assert 'test string' not in markdown.lower()
    assert '123' not in markdown

    realistic_terms = ['implement', 'test', 'system', 'service', 'feature']
    assert any(term in markdown.lower() for term in realistic_terms), (
        'Generated markdown should contain realistic domain terms'
    )
