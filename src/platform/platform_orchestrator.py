from pathlib import Path
from typing import Any

from .config_manager import ConfigManager
from .models import (
    PlanPlatformChangeRequest,
    PlanSetupRequest,
    PlanSetupWithRecommendationRequest,
    PlatformRequirements,
    ProjectConfig,
    TemplateGenerationRequest,
)
from .platform_selector import PlatformSelector, PlatformType
from .adapters import get_platform_adapter
from .template_coordinator import TemplateCoordinator
from .tui_adapters import get_tui_adapter
from .tui_selector import TuiType


class PlatformOrchestrator:
    def __init__(self, config_dir: str) -> None:
        self.platform_selector = PlatformSelector()
        self.template_coordinator = TemplateCoordinator()
        self.config_manager = ConfigManager(config_dir)

    @classmethod
    def create_with_default_config(cls) -> 'PlatformOrchestrator':
        default_config_dir = str(Path.home() / '.respec-ai' / 'projects')
        return cls(default_config_dir)

    def setup_project(self, request: PlanSetupRequest) -> ProjectConfig:
        requirements_dict = request.requirements.model_dump()
        if not self.platform_selector.validate_platform_choice(request.platform, requirements_dict):
            raise ValueError(f'Platform {request.platform.value} does not meet requirements: {requirements_dict}')

        config = ProjectConfig(
            project_path=request.project_path,
            platform=request.platform,
            requirements=request.requirements,
            config_data={},
        )
        self.config_manager.save_project_config(config)

        return config

    def setup_project_with_recommendation(self, request: PlanSetupWithRecommendationRequest) -> ProjectConfig:
        requirements_dict = request.requirements.model_dump()
        platform = self.platform_selector.recommend_platform(requirements_dict)

        config = ProjectConfig(
            project_path=request.project_path, platform=platform, requirements=request.requirements, config_data={}
        )
        self.config_manager.save_project_config(config)

        return config

    def setup_project_with_defaults(self, project_path: str, platform: PlatformType) -> ProjectConfig:
        # Explicit default requirements - no hidden behavior
        requirements = PlatformRequirements(supports_issues=True, supports_comments=True, real_time_collaboration=False)

        request = PlanSetupRequest(project_path=Path(project_path), platform=platform, requirements=requirements)

        return self.setup_project(request)

    def generate_command_template(self, request: TemplateGenerationRequest) -> str:
        config = self.config_manager.load_project_config(request.project_path)

        if not self.template_coordinator.validate_template_generation(request.command_name, config.platform):
            raise ValueError(f'Platform {config.platform.value} does not support command: {request.command_name}')

        configured_tui = config.config_data.get('tui', TuiType.CLAUDE_CODE.value)
        try:
            tui_adapter = get_tui_adapter(TuiType(configured_tui))
        except (ValueError, KeyError):
            tui_adapter = get_tui_adapter(TuiType.CLAUDE_CODE)

        return self.template_coordinator.generate_command_template(
            request.command_name, config.platform, tui_adapter=tui_adapter
        )

    def get_project_platform(self, project_path: str) -> PlatformType:
        return self.config_manager.get_project_platform(project_path)

    def get_platform_tools(self, project_path: str) -> dict[str, str]:
        config = self.config_manager.load_project_config(project_path)
        adapter = get_platform_adapter(config.platform)

        return {
            'create_plan_tool': adapter.create_plan_tool,
            'retrieve_plan_tool': adapter.retrieve_plan_tool,
            'update_plan_tool': adapter.update_plan_tool,
            'create_phase_tool': adapter.create_phase_tool,
            'retrieve_phase_tool': adapter.retrieve_phase_tool,
            'update_phase_tool': adapter.update_phase_tool,
            'comment_phase_tool': adapter.comment_phase_tool,
            'create_task_tool': adapter.create_task_tool,
            'retrieve_task_tool': adapter.retrieve_task_tool,
            'update_task_tool': adapter.update_task_tool,
            'list_phases_tool': adapter.list_phases_tool,
            'list_tasks_tool': adapter.list_tasks_tool,
        }

    def change_project_platform(self, request: PlanPlatformChangeRequest) -> None:
        existing_config = self.config_manager.load_project_config(request.project_path)

        requirements = request.requirements or existing_config.requirements

        requirements_dict = requirements.model_dump()
        if not self.platform_selector.validate_platform_choice(request.new_platform, requirements_dict):
            raise ValueError(f'Platform {request.new_platform.value} does not meet requirements: {requirements_dict}')

        updated_config = ProjectConfig(
            project_path=request.project_path,
            platform=request.new_platform,
            requirements=requirements,
            config_data=existing_config.config_data,
        )

        self.config_manager.save_project_config(updated_config)

    def list_configured_projects(self) -> list[ProjectConfig]:
        return self.config_manager.list_configured_projects()

    def get_available_platforms(self) -> list[PlatformType]:
        return self.platform_selector.get_available_platforms()

    def get_available_commands(self) -> list[str]:
        return self.template_coordinator.get_available_commands()

    def get_platform_capabilities(self, platform: PlatformType) -> dict[str, bool]:
        return self.platform_selector.get_platform_capabilities(platform)

    def recommend_platform_for_requirements(self, requirements: dict[str, bool]) -> PlatformType:
        return self.platform_selector.recommend_platform(requirements)

    def validate_project_setup(self, project_path: str) -> bool:
        try:
            config = self.config_manager.load_project_config(project_path)
        except ValueError:
            return False

        if config.platform not in self.get_available_platforms():
            return False

        requirements_dict = config.requirements.model_dump()
        if not self.platform_selector.validate_platform_choice(config.platform, requirements_dict):
            return False

        return True

    def get_project_info(self, project_path: str) -> dict[str, Any]:
        config = self.config_manager.load_project_config(project_path)

        platform_tools = self.get_platform_tools(project_path)
        platform_capabilities = self.platform_selector.get_platform_capabilities(config.platform)
        available_commands = [
            cmd
            for cmd in self.get_available_commands()
            if self.template_coordinator.validate_template_generation(cmd, config.platform)
        ]

        return {
            'project_path': config.project_path,
            'platform': config.platform.value,
            'platform_capabilities': platform_capabilities,
            'platform_tools': platform_tools,
            'available_commands': available_commands,
            'requirements': config.requirements.model_dump(),
            'config_valid': self.validate_project_setup(project_path),
        }
