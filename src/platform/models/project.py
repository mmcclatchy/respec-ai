from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from ..platform_selector import PlatformType
from ..tool_enums import RespecAICommand
from .core import PlatformModel


class ProjectStack(PlatformModel):
    language: str | None = Field(default=None, description='Primary language (e.g., python, javascript, go, rust)')
    languages: list[str] | None = Field(
        default=None,
        description='Detected/selected project languages in priority order',
    )
    backend_framework: str | None = Field(
        default=None, description='Backend framework (e.g., fastapi, fastmcp, flask, django, express)'
    )
    frontend_framework: str | None = Field(
        default=None, description='Frontend framework (e.g., react, next, vue, svelte)'
    )
    package_manager: str | None = Field(default=None, description='Package manager (e.g., uv, pip, npm, yarn)')
    runtime_version: str | None = Field(default=None, description='Language runtime version (e.g., 3.13, 22)')
    database: str | None = Field(default=None, description='Database (e.g., postgresql, sqlite, mongodb, neo4j)')
    api_style: str | None = Field(default=None, description='API style (e.g., rest, graphql, grpc, mcp)')
    async_runtime: bool | None = Field(default=None, description='Async runtime (True for async/await patterns)')
    type_checker: str | None = Field(default=None, description='Type checker (e.g., ty, mypy, pyright for Python)')
    css_framework: str | None = Field(default=None, description='CSS framework (e.g., tailwindcss, bootstrap)')
    ui_components: str | None = Field(default=None, description='UI component library (e.g., daisyui, shadcn)')
    architecture: str | None = Field(default=None, description='Architecture pattern (e.g., monolith, microservices)')


class LanguageTooling(PlatformModel):
    test_runner: str = Field(description='Test runner name (e.g., pytest, vitest)')
    test_command: str = Field(description='Command to run tests')
    coverage_command: str = Field(description='Command to run tests with coverage')
    checker: str = Field(description='Static checker name (e.g., mypy, tsc, cargo check)')
    check_command: str = Field(description='Command to run static checks')
    linter: str = Field(description='Linter name (e.g., ruff, eslint, clippy)')
    lint_command: str = Field(description='Command to run linter')


class ProjectToolingConfig(PlatformModel):
    tooling: dict[str, LanguageTooling] = Field(
        default_factory=dict,
        description='Language-keyed tooling configuration',
    )


class PlatformRequest(PlatformModel):
    project_path: Path = Field(description='Absolute path to the project')

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: Path) -> Path:
        if not v.is_absolute():
            raise ValueError('Project path must be absolute')
        return v


class PlatformRequirements(PlatformModel):
    supports_issues: bool = Field(description='Platform must support issue tracking')
    supports_comments: bool = Field(description='Platform must support commenting on items')
    supports_projects: bool = Field(default=False, description='Platform must support project management')
    supports_labels: bool = Field(default=False, description='Platform must support labeling/tagging')
    real_time_collaboration: bool = Field(default=False, description='Platform must support real-time collaboration')
    external_integration: bool = Field(default=False, description='Platform must support external integrations')


class PlanSetupRequest(PlatformRequest):
    platform: PlatformType = Field(description='Platform to use for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements that must be met')


class PlanSetupWithRecommendationRequest(PlatformRequest):
    requirements: PlatformRequirements = Field(description='Platform requirements for recommendation')


class PlanPlatformChangeRequest(PlatformRequest):
    new_platform: PlatformType = Field(description='New platform to use')
    requirements: PlatformRequirements | None = Field(
        default=None, description='Optional new requirements - if not provided, existing requirements are kept'
    )


class TemplateGenerationRequest(PlatformRequest):
    command_name: RespecAICommand = Field(description='Name of the command template to generate')


class ProjectConfig(PlatformRequest):
    platform: PlatformType = Field(description='Platform configured for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements for this project')
    config_data: dict[str, Any] = Field(default_factory=dict, description='Additional configuration data')
