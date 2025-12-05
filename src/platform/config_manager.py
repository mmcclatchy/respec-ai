import json
from pathlib import Path
from typing import Any
from pydantic import ValidationError

from .platform_selector import PlatformType
from .models import ProjectConfig


class ConfigManager:
    def __init__(self, config_dir: str) -> None:
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_project_config(self, config: ProjectConfig) -> None:
        config_file = self._get_config_file(config.project_path)

        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, 'w') as f:
            # Convert Path objects to strings for JSON serialization
            data = config.model_dump(mode='json')
            json.dump(data, f, indent=2)

    def load_project_config(self, project_path: str | Path) -> ProjectConfig:
        config_file = self._get_config_file(project_path)

        if not config_file.exists():
            raise ValueError(f'No configuration found for project: {project_path}. Run setup_project first.')

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            # Convert project_path back to Path object if it's a string
            if 'project_path' in data and isinstance(data['project_path'], str):
                data['project_path'] = Path(data['project_path'])
            return ProjectConfig.model_validate(data)
        except (json.JSONDecodeError, KeyError, ValueError, ValidationError) as e:
            raise ValueError(f'Invalid configuration file for project {project_path}: {e}')

    def get_project_platform(self, project_path: str | Path) -> PlatformType:
        config = self.load_project_config(project_path)
        return config.platform

    def delete_project_config(self, project_path: str | Path) -> None:
        config_file = self._get_config_file(project_path)

        if not config_file.exists():
            raise ValueError(f'No configuration found for project: {project_path}')

        config_file.unlink()

    def list_configured_projects(self) -> list[ProjectConfig]:
        configs: list[ProjectConfig] = []

        if not self.config_dir.exists():
            return configs

        for config_file in self.config_dir.rglob('platform.json'):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                # Convert project_path back to Path object if it's a string
                if 'project_path' in data and isinstance(data['project_path'], str):
                    data['project_path'] = Path(data['project_path'])
                configs.append(ProjectConfig.model_validate(data))
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip invalid config files
                continue

        return configs

    def update_project_config(self, project_path: str | Path, updates: dict[str, Any]) -> None:
        config = self.load_project_config(project_path)

        # Create updated config
        updated_config = ProjectConfig(
            project_path=config.project_path,
            platform=config.platform,
            requirements=config.requirements,
            config_data={**config.config_data, **updates},
        )

        # Save updated config
        self.save_project_config(updated_config)

    def _get_config_file(self, project_path: str | Path) -> Path:
        # Create safe filename from project path
        path_str = str(project_path)
        safe_name = path_str.replace('/', '_').replace('\\', '_')
        return self.config_dir / safe_name / 'platform.json'

    def _ensure_project_dir_exists(self, project_path: str | Path) -> None:
        config_file = self._get_config_file(project_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
