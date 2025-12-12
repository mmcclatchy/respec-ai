from src.models.phase import Phase


class TestAdditionalSections:
    def test_additional_sections_captured_from_markdown(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Build a web service

### Scope
API endpoints only

### Dependencies
Python 3.13+

### Deliverables
REST API

## System Design

### Architecture
Microservices architecture with API gateway

## Data Models

Entity relationships:
- User (1) <-> (N) Posts
- Post (1) <-> (N) Comments

## API Design

RESTful endpoints:
- GET /api/users
- POST /api/users
- GET /api/posts
- POST /api/posts

## Security Architecture

Authentication: JWT tokens
Authorization: RBAC

## Implementation

### Testing Strategy
Unit tests with pytest

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""

        phase = Phase.parse_markdown(markdown)

        assert phase.phase_name == 'test-phase'
        assert phase.objectives == 'Build a web service'
        assert phase.scope == 'API endpoints only'
        assert phase.architecture == 'Microservices architecture with API gateway'
        assert phase.testing_strategy == 'Unit tests with pytest'

        assert phase.additional_sections is not None
        assert 'Data Models' in phase.additional_sections
        assert 'API Design' in phase.additional_sections
        assert 'Security Architecture' in phase.additional_sections

        assert 'User (1) <-> (N) Posts' in phase.additional_sections['Data Models']
        assert 'GET /api/users' in phase.additional_sections['API Design']
        assert 'JWT tokens' in phase.additional_sections['Security Architecture']

    def test_additional_sections_in_build_markdown_output(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Build a CLI tool

### Scope
Command-line interface only

### Dependencies
Click library

### Deliverables
Executable binary

## System Design

### Architecture
Modular command structure

## CLI Commands

Available commands:
- init: Initialize project
- build: Build artifacts
- deploy: Deploy to server

## Configuration

Config file format: YAML
Default location: ~/.config/tool/config.yaml

## Implementation

### Testing Strategy
Integration tests with Click testing utilities

## Metadata

### Iteration
1

### Version
2

### Status
in-review
"""

        phase = Phase.parse_markdown(markdown)
        rebuilt_markdown = phase.build_markdown()

        assert 'CLI Commands' in rebuilt_markdown
        assert 'Configuration' in rebuilt_markdown
        assert 'init: Initialize project' in rebuilt_markdown
        assert 'Config file format: YAML' in rebuilt_markdown

        reparsed_phase = Phase.parse_markdown(rebuilt_markdown)

        assert reparsed_phase.phase_name == 'test-phase'
        assert reparsed_phase.additional_sections is not None
        assert 'CLI Commands' in reparsed_phase.additional_sections
        assert 'Configuration' in reparsed_phase.additional_sections

    def test_phase_without_additional_sections(self) -> None:
        markdown = """# Phase: minimal-phase

## Overview

### Objectives
Simple utility

### Scope
Single function

### Dependencies
None

### Deliverables
Python module

## System Design

### Architecture
Single module design

## Implementation

### Testing Strategy
Basic unit tests

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""

        phase = Phase.parse_markdown(markdown)

        assert phase.phase_name == 'minimal-phase'
        assert phase.additional_sections is None

        rebuilt_markdown = phase.build_markdown()
        assert 'minimal-phase' in rebuilt_markdown
        assert '## Metadata' in rebuilt_markdown

    def test_round_trip_with_complex_additional_sections(self) -> None:
        markdown = """# Phase: complex-phase

## Overview

### Objectives
Multi-tier application

### Scope
Full-stack development

### Dependencies
React, FastAPI, PostgreSQL

### Deliverables
Production-ready application

## System Design

### Architecture
Three-tier architecture: Frontend, Backend, Database

### Technology Stack
- Frontend: React 18
- Backend: FastAPI 0.115
- Database: PostgreSQL 16

## Data Models

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Design

### Authentication
POST /api/auth/login
POST /api/auth/logout

### Users
GET /api/users/:id
PUT /api/users/:id

### Posts
GET /api/posts
POST /api/posts
GET /api/posts/:id

## Security Architecture

### Authentication
- JWT tokens with 15-minute expiry
- Refresh tokens with 7-day expiry
- Secure httpOnly cookies

### Authorization
- Role-based access control (RBAC)
- Roles: admin, moderator, user
- Permission matrix enforced at API gateway

## Performance Requirements

### Response Times
- API endpoints: <200ms p95
- Database queries: <50ms p95
- Page load: <2s initial

### Scalability
- Support 10,000 concurrent users
- Handle 1,000 requests/second
- Database: 1TB capacity planning

## Deployment Architecture

### Infrastructure
- Platform: AWS
- Containerization: Docker + ECS
- Regions: us-east-1 (primary), us-west-2 (DR)

### Monitoring
- Metrics: CloudWatch
- Logging: CloudWatch Logs
- Tracing: X-Ray

## Implementation

### Functional Requirements
- User registration and authentication
- Post creation, editing, deletion
- Comment system
- Real-time notifications

### Non-Functional Requirements
- 99.9% uptime SLA
- Auto-scaling based on load
- Zero-downtime deployments

### Development Plan
1. Phase 1: Core authentication
2. Phase 2: Post management
3. Phase 3: Comment system
4. Phase 4: Real-time features

### Testing Strategy
- Unit tests: >80% coverage
- Integration tests: All API endpoints
- E2E tests: Critical user journeys
- Load tests: 10x expected traffic

## Additional Details

### Research Requirements
**Existing Documentation**:
- Read: ~/.claude/best-practices/react-hooks-2025.md
- Read: ~/.claude/best-practices/fastapi-patterns.md

**External Research Needed**:
- Synthesize: Real-time notification patterns with WebSockets in 2025
- Synthesize: PostgreSQL query optimization for high-concurrency workloads

### Success Criteria
- All API endpoints respond within SLA
- Zero critical security vulnerabilities
- >90% test coverage achieved
- Successful load test at 10,000 concurrent users

### Integration Context
- Integrates with existing authentication service
- Consumes user profile data from identity provider
- Publishes events to central event bus

## Metadata

### Iteration
2

### Version
3

### Status
approved
"""

        phase = Phase.parse_markdown(markdown)

        assert phase.phase_name == 'complex-phase'
        assert phase.iteration == 2
        assert phase.version == 3

        assert phase.additional_sections is not None
        assert len(phase.additional_sections) == 5
        assert 'Data Models' in phase.additional_sections
        assert 'API Design' in phase.additional_sections
        assert 'Security Architecture' in phase.additional_sections
        assert 'Performance Requirements' in phase.additional_sections
        assert 'Deployment Architecture' in phase.additional_sections

        rebuilt_markdown = phase.build_markdown()

        reparsed_phase = Phase.parse_markdown(rebuilt_markdown)

        assert reparsed_phase.phase_name == 'complex-phase'
        assert reparsed_phase.iteration == 2
        assert reparsed_phase.version == 3
        assert reparsed_phase.objectives == phase.objectives
        assert reparsed_phase.scope == phase.scope
        assert reparsed_phase.architecture == phase.architecture
        assert reparsed_phase.technology_stack == phase.technology_stack
        assert reparsed_phase.functional_requirements == phase.functional_requirements

        assert reparsed_phase.additional_sections is not None
        assert len(reparsed_phase.additional_sections) == 5
        assert 'CREATE TABLE users' in reparsed_phase.additional_sections['Data Models']
        assert 'POST /api/auth/login' in reparsed_phase.additional_sections['API Design']
        assert 'JWT tokens' in reparsed_phase.additional_sections['Security Architecture']
        assert '<200ms p95' in reparsed_phase.additional_sections['Performance Requirements']
        assert 'CloudWatch' in reparsed_phase.additional_sections['Deployment Architecture']
