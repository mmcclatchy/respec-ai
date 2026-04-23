import inspect
import re
from collections.abc import Mapping
from importlib import import_module
from typing import Any

import pytest
from pydantic import BaseModel

import src.platform.models as legacy_models

try:
    split_models = import_module('src.platform.models_next')
except ModuleNotFoundError:
    split_models = None


def _model_classes(module: Any, module_prefix: str) -> dict[str, type[Any]]:
    classes: dict[str, type[Any]] = {}
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if not obj.__module__.startswith(module_prefix):
            continue
        classes[name] = obj
    return classes


def _normalize_model_config(model_config: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(model_config, Mapping):
        return dict(model_config)
    return {}


def _normalize_annotation(annotation: Any) -> str:
    normalized = repr(annotation)
    normalized = re.sub(r'(?:[a-z_][a-z0-9_]*\.)+', '', normalized)
    return normalized


def test_split_module_preserves_legacy_model_set_and_schema() -> None:
    if split_models is None:
        pytest.skip('models_next package removed after cutover; parity verified during migration stage')

    legacy_classes = _model_classes(legacy_models, 'src.platform.models')
    split_classes = _model_classes(split_models, 'src.platform.models_next')

    assert set(legacy_classes.keys()) == set(split_classes.keys())

    for class_name in sorted(legacy_classes.keys()):
        legacy_cls = legacy_classes[class_name]
        split_cls = split_classes[class_name]

        # Field parity (names, required/defaults, annotations, descriptions)
        legacy_fields = legacy_cls.model_fields
        split_fields = split_cls.model_fields
        assert set(legacy_fields.keys()) == set(split_fields.keys()), class_name

        for field_name in sorted(legacy_fields.keys()):
            legacy_field = legacy_fields[field_name]
            split_field = split_fields[field_name]

            assert legacy_field.is_required() == split_field.is_required(), f'{class_name}.{field_name} required'
            assert legacy_field.description == split_field.description, f'{class_name}.{field_name} description'
            assert legacy_field.default == split_field.default, f'{class_name}.{field_name} default'
            assert (legacy_field.default_factory is None) == (split_field.default_factory is None), (
                f'{class_name}.{field_name} default_factory'
            )
            assert _normalize_annotation(legacy_field.annotation) == _normalize_annotation(split_field.annotation), (
                f'{class_name}.{field_name} annotation'
            )

        # Computed field parity
        legacy_computed = set(getattr(legacy_cls, 'model_computed_fields', {}).keys())
        split_computed = set(getattr(split_cls, 'model_computed_fields', {}).keys())
        assert legacy_computed == split_computed, class_name

        # Class-level tool constants parity where applicable
        for attr_name in ('respec_ai_tools', 'builtin_tools'):
            legacy_has = hasattr(legacy_cls, attr_name)
            split_has = hasattr(split_cls, attr_name)
            assert legacy_has == split_has, f'{class_name}.{attr_name} presence'
            if legacy_has and split_has:
                assert getattr(legacy_cls, attr_name) == getattr(split_cls, attr_name), (
                    f'{class_name}.{attr_name} value'
                )

        # Model config parity
        if issubclass(legacy_cls, BaseModel) and issubclass(split_cls, BaseModel):
            assert _normalize_model_config(legacy_cls.model_config) == _normalize_model_config(split_cls.model_config)
