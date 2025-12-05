import pytest
from src.models.build_plan import BuildPlan
from src.models.enums import BuildStatus


class TestBuildPlanParsing:
    def test_parse_markdown_extracts_all_fields(self) -> None:
        markdown = """# Build Plan: E-Commerce Platform

## Project Overview

### Goal
Build a scalable e-commerce platform

### Duration
6 months

### Team Size
5 developers

## Technology Stack

### Primary Language
Python

### Framework
FastAPI

### Database
PostgreSQL

## Architecture

### Development Environment
Docker-based development with automated testing pipeline

### Database Schema
User tables, product catalog, order management with proper indexing

### API Architecture
RESTful API with authentication and rate limiting

### Frontend Architecture
React SPA with TypeScript and state management

## Implementation

### Core Features
User auth, product catalog, shopping cart, payment processing

### Integration Points
Payment gateway, shipping APIs, inventory management

## Quality Management

### Testing Strategy
Unit tests, integration tests, E2E testing with Playwright

### Code Standards
PEP 8 for Python, ESLint for TypeScript, pre-commit hooks

### Performance Requirements
Sub-2s page loads, 1000+ concurrent users, 99.9% uptime

### Security Implementation
HTTPS, JWT tokens, input validation, SQL injection prevention

## Metadata

### Status
in-progress

"""

        build_plan = BuildPlan.parse_markdown(markdown)

        assert build_plan.project_name == 'E-Commerce Platform'
        assert build_plan.project_goal == 'Build a scalable e-commerce platform'
        assert build_plan.total_duration == '6 months'
        assert build_plan.team_size == '5 developers'
        assert build_plan.primary_language == 'Python'
        assert build_plan.framework == 'FastAPI'
        assert build_plan.database == 'PostgreSQL'
        assert build_plan.development_environment == 'Docker-based development with automated testing pipeline'
        assert build_plan.database_schema == 'User tables, product catalog, order management with proper indexing'
        assert build_plan.api_architecture == 'RESTful API with authentication and rate limiting'
        assert build_plan.frontend_architecture == 'React SPA with TypeScript and state management'
        assert build_plan.core_features == 'User auth, product catalog, shopping cart, payment processing'
        assert build_plan.integration_points == 'Payment gateway, shipping APIs, inventory management'
        assert build_plan.testing_strategy == 'Unit tests, integration tests, E2E testing with Playwright'
        assert build_plan.code_standards == 'PEP 8 for Python, ESLint for TypeScript, pre-commit hooks'
        assert build_plan.performance_requirements == 'Sub-2s page loads, 1000+ concurrent users, 99.9% uptime'
        assert build_plan.security_implementation == 'HTTPS, JWT tokens, input validation, SQL injection prevention'
        assert build_plan.build_status == BuildStatus.IN_PROGRESS

    def test_parse_markdown_handles_missing_sections(self) -> None:
        markdown = """# Build Plan: Minimal Project

## Project Overview

### Goal
Simple project

### Duration
3 months

### Team Size
2 developers

## Technology Stack

### Primary Language
JavaScript

### Framework
Express

### Database
MongoDB

## Architecture

### Development Environment
Basic Node.js setup

## Metadata

### Status
planning

"""

        build_plan = BuildPlan.parse_markdown(markdown)

        assert build_plan.project_name == 'Minimal Project'
        assert build_plan.project_goal == 'Simple project'
        assert build_plan.development_environment == 'Basic Node.js setup'
        # Missing sections should have default values
        assert 'Database Schema not specified' in build_plan.database_schema
        assert 'Api Architecture not specified' in build_plan.api_architecture

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = """This is not a build plan format"""

        with pytest.raises(ValueError, match='Invalid build plan format: missing title'):
            BuildPlan.parse_markdown(invalid_markdown)


class TestBuildPlanMarkdownBuilding:
    @pytest.fixture
    def sample_build_plan(self) -> BuildPlan:
        return BuildPlan(
            project_name='Test Project',
            project_goal='Build a test application',
            total_duration='4 months',
            team_size='3 developers',
            primary_language='Python',
            framework='Django',
            database='SQLite',
            development_environment='Local development with virtual env',
            database_schema='Simple user and content tables',
            api_architecture='REST API with Django REST Framework',
            frontend_architecture='Server-side rendering with Django templates',
            core_features='User registration, content creation, basic search',
            integration_points='Email service, file storage',
            testing_strategy='Django test framework with coverage',
            code_standards='Black formatter, isort, flake8',
            performance_requirements='Handle 100 concurrent users',
            security_implementation='Django security middleware, CSRF protection',
            build_status=BuildStatus.PLANNING,
        )

    def test_build_markdown_creates_valid_template_format(self, sample_build_plan: BuildPlan) -> None:
        markdown = sample_build_plan.build_markdown()

        assert '# Build Plan: Test Project' in markdown
        assert '## Project Overview' in markdown
        assert '### Goal' in markdown
        assert 'Build a test application' in markdown
        assert '## Technology Stack' in markdown
        assert '### Primary Language' in markdown
        assert 'Python' in markdown
        assert '## Architecture' in markdown
        assert '### Development Environment' in markdown
        assert 'Local development with virtual env' in markdown
        assert '### Status\nplanning' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_build_plan: BuildPlan) -> None:
        # Build markdown from the model
        markdown = sample_build_plan.build_markdown()

        # Parse it back into a model
        parsed_build_plan = BuildPlan.parse_markdown(markdown)

        # Should match original (except timestamps)
        assert parsed_build_plan.project_name == sample_build_plan.project_name
        assert parsed_build_plan.project_goal == sample_build_plan.project_goal
        assert parsed_build_plan.total_duration == sample_build_plan.total_duration
        assert parsed_build_plan.team_size == sample_build_plan.team_size
        assert parsed_build_plan.primary_language == sample_build_plan.primary_language
        assert parsed_build_plan.framework == sample_build_plan.framework
        assert parsed_build_plan.database == sample_build_plan.database
        assert parsed_build_plan.development_environment == sample_build_plan.development_environment
        assert parsed_build_plan.database_schema == sample_build_plan.database_schema
        assert parsed_build_plan.api_architecture == sample_build_plan.api_architecture
        assert parsed_build_plan.frontend_architecture == sample_build_plan.frontend_architecture
        assert parsed_build_plan.core_features == sample_build_plan.core_features
        assert parsed_build_plan.integration_points == sample_build_plan.integration_points
        assert parsed_build_plan.testing_strategy == sample_build_plan.testing_strategy
        assert parsed_build_plan.code_standards == sample_build_plan.code_standards
        assert parsed_build_plan.performance_requirements == sample_build_plan.performance_requirements
        assert parsed_build_plan.security_implementation == sample_build_plan.security_implementation
        assert parsed_build_plan.build_status == sample_build_plan.build_status

    def test_character_for_character_round_trip_validation(self, sample_build_plan: BuildPlan) -> None:
        # Build markdown
        original_markdown = sample_build_plan.build_markdown()

        # Parse and rebuild
        parsed_build_plan = BuildPlan.parse_markdown(original_markdown)
        rebuilt_markdown = parsed_build_plan.build_markdown()

        # Should be identical
        assert original_markdown == rebuilt_markdown
