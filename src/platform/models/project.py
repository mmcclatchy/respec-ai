from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from ..platform_selector import PlatformType
from ..tool_enums import RespecAICommand
from .core import PlatformModel


class LanguageStackProfile(PlatformModel):
    frontend_framework: str | None = Field(
        default=None, description='Frontend framework for this language (e.g., react, next, vue, svelte)'
    )
    css_framework: str | None = Field(
        default=None, description='CSS framework for this language (e.g., tailwindcss, bootstrap)'
    )
    ui_components: str | None = Field(
        default=None, description='UI component library for this language (e.g., daisyui, shadcn)'
    )
    package_manager: str | None = Field(
        default=None, description='Package manager for this language (e.g., uv, pip, npm, yarn)'
    )
    runtime_version: str | None = Field(default=None, description='Language runtime version (e.g., 3.13, 22)')
    type_checker: str | None = Field(
        default=None, description='Type checker for this language (e.g., ty, mypy, pyright, tsc)'
    )
    dev_command: str | None = Field(default=None, description="Command to start this language's dev server")
    base_url: str | None = Field(default=None, description='Base URL the dev server serves once started')
    seed_command: str | None = Field(
        default=None, description='Optional command to seed application state before a preflight review'
    )
    storage_state_path: str | None = Field(
        default=None,
        description='Path to a saved browser storage-state file for authenticated preflight checks',
    )


class ProjectStack(PlatformModel):
    language: str | None = Field(default=None, description='Primary language (e.g., python, javascript, go, rust)')
    languages: list[str] | None = Field(
        default=None,
        description='Detected/selected project languages in priority order',
    )
    backend_framework: str | None = Field(
        default=None, description='Backend framework (e.g., fastapi, fastmcp, flask, django, express)'
    )
    database: str | None = Field(default=None, description='Database (e.g., postgresql, sqlite, mongodb, neo4j)')
    api_style: str | None = Field(default=None, description='API style (e.g., rest, graphql, grpc, mcp)')
    async_runtime: bool | None = Field(default=None, description='Async runtime (True for async/await patterns)')
    architecture: str | None = Field(default=None, description='Architecture pattern (e.g., monolith, microservices)')
    language_stack: dict[str, LanguageStackProfile] = Field(
        default_factory=dict,
        description='Per-language stack attributes (frontend framework, styling, package manager, '
        'runtime, type checker, dev server) keyed by language name',
    )


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
