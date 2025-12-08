import os
from enum import StrEnum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoopConfig(BaseSettings):
    model_config = SettingsConfigDict(
        extra='forbid',
        env_prefix='LOOP_',
    )

    plan_threshold: int = Field(default=90, ge=1, le=100)
    analyst_threshold: int = Field(default=90, ge=1, le=100)
    roadmap_threshold: int = Field(default=90, ge=1, le=100)
    spec_threshold: int = Field(default=90, ge=1, le=100)
    build_plan_threshold: int = Field(default=90, ge=1, le=100)
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

    spec_length_soft_cap: int = Field(
        default=40_000, ge=30_000, le=60_000, description='Soft cap for spec length in characters (~10k tokens)'
    )


class LogLevel(StrEnum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='forbid',
        env_prefix='MCP_',
    )

    server_name: str = 'respec-ai'
    host: str = '0.0.0.0'
    port: int = 8000
    debug: bool = False

    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.DEBUG, description='Logging level')
    log_file: str | None = Field(
        default='logs/mcp-server.log',
        description='Log file path. Set to "stdout" for container environments, or absolute path for file logging. None = stderr only',
    )

    # State Manager Configuration
    state_manager: str = Field(default='memory', description='State manager type: memory or database')

    @field_validator('state_manager')
    @classmethod
    def validate_state_manager(cls, v: str) -> str:
        allowed = {'memory', 'database'}
        if v.lower() not in allowed:
            raise ValueError(f'state_manager must be one of {allowed}, got: {v}')
        return v.lower()


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='forbid',
        env_prefix='DATABASE_',
    )

    url: str = Field(
        default_factory=lambda: (
            'postgresql://respec:respec@localhost:5433/respec_test'
            if os.getenv('TESTING', '').lower() == 'true'
            else 'postgresql://respec:respec@localhost:5433/respec_dev'
        ),
        description='PostgreSQL connection URL',
    )
    pool_min_size: int = Field(default=5, ge=1, le=50)
    pool_max_size: int = Field(default=20, ge=1, le=100)
    pool_timeout: float = Field(default=30.0, ge=1.0, le=120.0)
    command_timeout: float = Field(default=60.0, ge=1.0, le=300.0)
    max_inactive_connection_lifetime: float = Field(default=300.0, ge=60.0)


loop_config = LoopConfig()
mcp_settings = MCPSettings()
database_settings = DatabaseSettings()
