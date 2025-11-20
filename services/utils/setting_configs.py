from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoopConfig(BaseSettings):
    model_config = SettingsConfigDict(
        extra='forbid',
        env_prefix='LOOP_',
    )

    plan_threshold: int = Field(default=85, ge=1, le=100)
    analyst_threshold: int = Field(default=90, ge=1, le=100)
    roadmap_threshold: int = Field(default=90, ge=1, le=100)
    spec_threshold: int = Field(default=85, ge=1, le=100)
    build_plan_threshold: int = Field(default=80, ge=1, le=100)
    build_code_threshold: int = Field(default=95, ge=1, le=100)

    plan_improvement_threshold: int = Field(default=5, ge=1, le=100)
    analyst_improvement_threshold: int = Field(default=10, ge=1, le=100)
    roadmap_improvement_threshold: int = Field(default=10, ge=1, le=100)
    spec_improvement_threshold: int = Field(default=5, ge=1, le=100)
    build_plan_improvement_threshold: int = Field(default=5, ge=1, le=100)
    build_code_improvement_threshold: int = Field(default=5, ge=1, le=100)

    plan_checkpoint_frequency: int = Field(default=5, ge=1, le=20)
    analyst_checkpoint_frequency: int = Field(default=3, ge=1, le=20)
    roadmap_checkpoint_frequency: int = Field(default=5, ge=1, le=20)
    spec_checkpoint_frequency: int = Field(default=5, ge=1, le=20)
    build_plan_checkpoint_frequency: int = Field(default=5, ge=1, le=20)
    build_code_checkpoint_frequency: int = Field(default=5, ge=1, le=20)


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='forbid',
        env_prefix='MCP_',
    )

    server_name: str = 'specter'
    host: str = '0.0.0.0'
    port: int = 8000
    debug: bool = False

    # Logging configuration
    log_level: str = Field(default='INFO', description='Logging level: DEBUG, INFO, WARNING, ERROR')
    log_file: str | None = Field(
        default='mcp-server.log',
        description='Log file path. Set to "stdout" for container environments, or absolute path for file logging. None = stderr only',
    )


loop_config = LoopConfig()
mcp_settings = MCPSettings()
