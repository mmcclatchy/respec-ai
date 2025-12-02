"""Format preservation tests for TechnicalSpec model.

These tests verify that complex markdown formatting (bullet lists, code blocks,
nested lists, etc.) is preserved through parse → build → parse cycles.
"""

import pytest

from services.models.spec import TechnicalSpec


@pytest.fixture
def spec_with_bullet_lists() -> str:
    return """# Technical Specification: authentication-system

## Overview

### Objectives
Implement secure user authentication

### Scope
Login, logout, and session management

### Dependencies
- PostgreSQL database for user storage
- Redis for session management
- JWT library for token generation

### Deliverables
- Working authentication API
- User registration endpoint
- Password reset functionality

## System Design

### Architecture
Microservice architecture with the following components:
- Auth service handles login/logout
- Token service manages JWT generation
- Session service maintains active sessions

### Technology Stack
- Python 3.11+ with FastAPI framework
- PostgreSQL 15 for persistent storage
- Redis 7 for session caching
- JWT tokens for stateless authentication

## Implementation

### Functional Requirements
The system must support:
- User registration with email validation
- Secure password hashing with bcrypt
- Session management with configurable timeouts
- Multi-factor authentication support

### Non-Functional Requirements
- Response time under 100ms for authentication
- Support 10,000 concurrent sessions
- 99.99% uptime requirement
- GDPR-compliant data handling

### Development Plan
Implementation will proceed in phases:
- Phase 1: Core authentication (login/logout)
- Phase 2: Registration and password reset
- Phase 3: MFA and advanced security features

### Testing Strategy
Comprehensive testing approach:
- Unit tests for all auth logic
- Integration tests with database
- Security penetration testing
- Load testing for concurrent users

## Additional Details

### Research Requirements
- OAuth 2.0 integration patterns
- OIDC implementation best practices
- JWT security considerations
- Session fixation attack prevention

### Success Criteria
- All security tests pass
- 100% code coverage achieved
- Performance benchmarks met
- Security audit completed successfully

### Integration Context
Integrates with:
- User service for profile data
- Email service for notifications
- Audit service for security logging

## Metadata

### Status
draft

### Iteration
0

### Version
1.0
"""


@pytest.fixture
def spec_with_mixed_content() -> str:
    return """# Technical Specification: data-pipeline

## Overview

### Objectives
Build a scalable data processing pipeline that can handle large volumes of data.

The pipeline must support real-time and batch processing modes.

### Scope
This specification covers the following areas:
- Data ingestion from multiple sources
- Transformation and validation
- Storage and archival

Additional considerations include error handling and monitoring.

### Dependencies
External services and libraries required

### Deliverables
Working pipeline implementation

## System Design

### Architecture
The architecture follows a lambda pattern with both batch and streaming layers.

Key components:
- Ingestion layer for data collection
- Processing layer for transformations
- Storage layer for persistence

### Technology Stack
Python-based stack with modern libraries

## Implementation

### Functional Requirements
Core functionality includes data validation and transformation.

Required features:
- Schema validation for incoming data
- Data quality checks
- Error recovery mechanisms

All data must be validated before processing.

### Non-Functional Requirements
Performance and reliability requirements

### Development Plan
Phased implementation approach

### Testing Strategy
Comprehensive testing coverage

## Additional Details

### Research Requirements
Technology research needed

### Success Criteria
Quality gates for completion

### Integration Context
System integration points

## Metadata

### Status
in-development
"""


def test_bullet_list_content_preserved_in_dependencies(spec_with_bullet_lists: str) -> None:
    original_markdown = spec_with_bullet_lists

    spec = TechnicalSpec.parse_markdown(original_markdown)

    assert 'PostgreSQL database for user storage' in spec.dependencies
    assert 'Redis for session management' in spec.dependencies
    assert 'JWT library for token generation' in spec.dependencies

    rebuilt_markdown = spec.build_markdown()
    reparsed_spec = TechnicalSpec.parse_markdown(rebuilt_markdown)

    assert spec.dependencies == reparsed_spec.dependencies, 'Dependencies content changed during round-trip'


def test_bullet_list_content_preserved_in_deliverables(spec_with_bullet_lists: str) -> None:
    original_markdown = spec_with_bullet_lists

    spec = TechnicalSpec.parse_markdown(original_markdown)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert 'Working authentication API' in spec.deliverables
    assert 'User registration endpoint' in spec.deliverables
    assert 'Password reset functionality' in spec.deliverables

    assert spec.deliverables == reparsed.deliverables, 'Deliverables content changed during round-trip'


def test_bullet_list_content_preserved_in_architecture(spec_with_bullet_lists: str) -> None:
    original_markdown = spec_with_bullet_lists

    spec = TechnicalSpec.parse_markdown(original_markdown)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert isinstance(spec.architecture, str)
    assert 'Auth service handles login/logout' in spec.architecture
    assert 'Token service manages JWT generation' in spec.architecture
    assert 'Session service maintains active sessions' in spec.architecture

    assert spec.architecture == reparsed.architecture, 'Architecture content changed during round-trip'


def test_mixed_content_format_preserved(spec_with_mixed_content: str) -> None:
    original_markdown = spec_with_mixed_content

    spec = TechnicalSpec.parse_markdown(original_markdown)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert 'scalable data processing pipeline' in spec.objectives
    assert 'real-time and batch processing' in spec.objectives

    assert 'Data ingestion from multiple sources' in spec.scope
    assert 'Transformation and validation' in spec.scope
    assert 'Additional considerations include' in spec.scope or 'error handling and monitoring' in spec.scope

    assert spec.objectives == reparsed.objectives, 'Objectives content changed during round-trip'
    assert spec.scope == reparsed.scope, 'Scope content changed during round-trip'


def test_plain_text_content_still_works() -> None:
    markdown = """# Technical Specification: simple-spec

## Overview

### Objectives
Basic functionality without lists

### Scope
Simple plain text scope

### Dependencies
No external dependencies

### Deliverables
Single deliverable

## Metadata

### Status
draft
"""

    spec = TechnicalSpec.parse_markdown(markdown)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert spec.objectives == 'Basic functionality without lists'
    assert spec.objectives == reparsed.objectives


def test_character_for_character_round_trip(spec_with_bullet_lists: str) -> None:
    original_markdown = spec_with_bullet_lists

    first_parse = TechnicalSpec.parse_markdown(original_markdown)
    first_build = first_parse.build_markdown()
    second_parse = TechnicalSpec.parse_markdown(first_build)
    second_build = second_parse.build_markdown()

    assert first_build == second_build, 'Markdown changed between first and second round-trip'


def test_ordered_lists_preserved() -> None:
    markdown_with_ordered_lists = """# Technical Specification: ordered-implementation

## Overview

### Objectives
Sequential implementation steps

### Scope
Phased delivery approach

### Dependencies
External dependencies

### Deliverables
Staged deliverables

## Implementation

### Functional Requirements
1. First requirement: User authentication with email
2. Second requirement: Password reset via email link
3. Third requirement: Session management with Redis

### Non-Functional Requirements
1. Performance: Response time under 200ms
2. Scalability: Support 10,000 concurrent users
3. Security: HTTPS and JWT token encryption

### Development Plan
1. Phase 1: Setup development environment
2. Phase 2: Implement core authentication
3. Phase 3: Add password reset feature
4. Phase 4: Implement session management

### Testing Strategy
Testing phases

## Metadata

### Status
draft
"""

    spec = TechnicalSpec.parse_markdown(markdown_with_ordered_lists)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert isinstance(spec.functional_requirements, str)
    assert isinstance(spec.development_plan, str)

    assert 'First requirement: User authentication' in spec.functional_requirements
    assert 'Second requirement: Password reset' in spec.functional_requirements
    assert 'Third requirement: Session management' in spec.functional_requirements

    assert 'Phase 1: Setup development environment' in spec.development_plan
    assert 'Phase 2: Implement core authentication' in spec.development_plan

    assert spec.functional_requirements == reparsed.functional_requirements, (
        'Ordered list content changed during round-trip'
    )
    assert spec.development_plan == reparsed.development_plan, 'Development plan changed during round-trip'


def test_code_blocks_preserved() -> None:
    markdown_with_code_blocks = """# Technical Specification: api-implementation

## Overview

### Objectives
Implement RESTful API endpoints

### Scope
User management API

### Dependencies
FastAPI framework

### Deliverables
Working API service

## Implementation

### Functional Requirements
The API will implement the following authentication endpoint:

```python
@app.post("/api/auth/login")
async def login(credentials: LoginRequest) -> TokenResponse:
    user = await authenticate_user(credentials)
    return generate_token(user)
```

Additional endpoints for registration and logout will follow the same pattern.

### Non-Functional Requirements
Performance requirements include:

```yaml
response_time:
  p50: 50ms
  p95: 150ms
  p99: 300ms
concurrent_users: 10000
```

### Development Plan
Implementation strategy

### Testing Strategy
Test cases will include:

```javascript
describe('Authentication API', () => {
  it('should return token on valid login', async () => {
    const response = await login(validCredentials);
    expect(response.token).toBeDefined();
  });
});
```

## Metadata

### Status
draft
"""

    spec = TechnicalSpec.parse_markdown(markdown_with_code_blocks)
    rebuilt = spec.build_markdown()
    reparsed = TechnicalSpec.parse_markdown(rebuilt)

    assert isinstance(spec.functional_requirements, str)
    assert isinstance(spec.non_functional_requirements, str)
    assert isinstance(spec.testing_strategy, str)

    assert (
        '@app.post("/api/auth/login")' in spec.functional_requirements
        or 'authenticate_user' in spec.functional_requirements
    )
    assert 'async def login' in spec.functional_requirements or 'login' in spec.functional_requirements

    assert 'response_time' in spec.non_functional_requirements or 'p50: 50ms' in spec.non_functional_requirements

    assert 'describe' in spec.testing_strategy or 'Authentication API' in spec.testing_strategy

    assert spec.functional_requirements == reparsed.functional_requirements, (
        'Code blocks in functional requirements changed during round-trip'
    )
    assert spec.non_functional_requirements == reparsed.non_functional_requirements, (
        'Code blocks in non-functional requirements changed during round-trip'
    )
    assert spec.testing_strategy == reparsed.testing_strategy, (
        'Code blocks in testing strategy changed during round-trip'
    )
