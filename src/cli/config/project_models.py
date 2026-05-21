import json
from pathlib import Path
from typing import Any

from src.platform.tui_selector import TuiType


def project_config_path(project_path: Path) -> Path:
    return project_path / '.respec-ai' / 'config.json'


def load_project_config_if_exists(project_path: Path) -> dict[str, Any] | None:
    path = project_config_path(project_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def save_project_config(project_path: Path, config: dict[str, Any]) -> None:
    path = project_config_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _string_map(values: object) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    mapped: dict[str, str] = {}
    for key, value in values.items():
        if isinstance(key, str) and isinstance(value, str):
            mapped[key] = value
    return mapped


def get_project_model_overrides(config: dict[str, Any], provider: str) -> dict[str, str]:
    models = config.get('models')
    if not isinstance(models, dict):
        return {}
    return _string_map(models.get(provider))


def set_project_model_overrides(config: dict[str, Any], provider: str, models: dict[str, str]) -> None:
    if 'models' not in config or not isinstance(config['models'], dict):
        config['models'] = {}
    config_models = config['models']
    assert isinstance(config_models, dict)
    config_models[provider] = models


def provider_for_tui(tui: TuiType | str) -> str | None:
    value = tui.value if isinstance(tui, TuiType) else str(tui)
    if value == TuiType.CODEX.value:
        return 'codex'
    if value == TuiType.OPENCODE.value:
        return 'opencode'
    return None
