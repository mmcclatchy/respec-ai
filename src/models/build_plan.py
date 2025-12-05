from typing import ClassVar

from .base import MCPModel
from .enums import BuildStatus


class BuildPlan(MCPModel):
    # Class configuration for MCPModel
    TITLE_PATTERN: ClassVar[str] = '# Build Plan'
    TITLE_FIELD: ClassVar[str] = 'project_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'project_goal': ('Project Overview', 'Goal'),
        'total_duration': ('Project Overview', 'Duration'),
        'team_size': ('Project Overview', 'Team Size'),
        'primary_language': ('Technology Stack', 'Primary Language'),
        'framework': ('Technology Stack', 'Framework'),
        'database': ('Technology Stack', 'Database'),
        'development_environment': ('Architecture', 'Development Environment'),
        'database_schema': ('Architecture', 'Database Schema'),
        'api_architecture': ('Architecture', 'API Architecture'),
        'frontend_architecture': ('Architecture', 'Frontend Architecture'),
        'core_features': ('Implementation', 'Core Features'),
        'integration_points': ('Implementation', 'Integration Points'),
        'testing_strategy': ('Quality Management', 'Testing Strategy'),
        'code_standards': ('Quality Management', 'Code Standards'),
        'performance_requirements': ('Quality Management', 'Performance Requirements'),
        'security_implementation': ('Quality Management', 'Security Implementation'),
        'build_status': ('Metadata', 'Status'),
    }

    # Model fields with defaults
    project_name: str = 'Unnamed Project'
    project_goal: str = 'Project Goal not specified'
    total_duration: str = 'Total Duration not specified'
    team_size: str = 'Team Size not specified'
    primary_language: str = 'Primary Language not specified'
    framework: str = 'Framework not specified'
    database: str = 'Database not specified'
    development_environment: str = 'Development Environment not specified'
    database_schema: str = 'Database Schema not specified'
    api_architecture: str = 'Api Architecture not specified'
    frontend_architecture: str = 'Frontend Architecture not specified'
    core_features: str = 'Core Features not specified'
    integration_points: str = 'Integration Points not specified'
    testing_strategy: str = 'Testing Strategy not specified'
    code_standards: str = 'Code Standards not specified'
    performance_requirements: str = 'Performance Requirements not specified'
    security_implementation: str = 'Security Implementation not specified'
    build_status: BuildStatus = BuildStatus.PLANNING

    def build_markdown(self) -> str:
        return f"""{self.TITLE_PATTERN}: {self.project_name}

## Project Overview

### Goal
{self.project_goal}

### Duration
{self.total_duration}

### Team Size
{self.team_size}

## Technology Stack

### Primary Language
{self.primary_language}

### Framework
{self.framework}

### Database
{self.database}

## Architecture

### Development Environment
{self.development_environment}

### Database Schema
{self.database_schema}

### API Architecture
{self.api_architecture}

### Frontend Architecture
{self.frontend_architecture}

## Implementation

### Core Features
{self.core_features}

### Integration Points
{self.integration_points}

## Quality Management

### Testing Strategy
{self.testing_strategy}

### Code Standards
{self.code_standards}

### Performance Requirements
{self.performance_requirements}

### Security Implementation
{self.security_implementation}

## Metadata

### Status
{self.build_status.value}
"""
