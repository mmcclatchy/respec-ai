# Coding Standards Template

This file serves as a reference template for `.respec-ai/coding-standards.md` in user projects.

## Purpose

The `.respec-ai/coding-standards.md` file allows users to customize coding standards that the `build-coder` agent will follow when generating code. This file should be created in the user's project workspace (not in the MCP server).

## Location

```text
{user-project-workspace}/.respec-ai/coding-standards.md
```

## Usage by build-coder Agent

The `build-coder` agent reads this file at the start of each coding iteration and applies all rules to generated code. If the file doesn't exist, the agent falls back to BuildPlan Code Standards section or general Python best practices.

## Template Structure

- Below is a template that users can customize for their projects:

    ```markdown
    # Project Coding Standards
    
    ## Documentation Rules
    
    ### Docstrings
    - **Required for**:
      - Public API functions and classes
      - Complex algorithms where "why" isn't obvious
      - Functions with non-obvious side effects
    - **NOT required for**:
      - Private functions (prefixed with `_`)
      - Simple getters/setters
      - Obvious CRUD operations
      - Test functions
    
    ### Comments
    - **Use for**:
      - Non-obvious business logic
      - Complex algorithms or mathematical operations
      - Regulatory/compliance requirements
      - Workarounds for known issues
    - **NEVER use for**:
      - Obvious operations
      - Restating what code already says
      - Variable declarations
    
    ### Examples
    
        ```python
        # ❌ BAD: Obvious docstring
        def get_user_name(self) -> str:
            """Get the user name."""
            return self.name
        
        # ✅ GOOD: No unnecessary documentation
        def get_user_name(self) -> str:
            return self.name
        
        # ✅ GOOD: Complex logic documented
        def calculate_risk_score(self, factors: dict[str, float]) -> float:
            """Calculate risk score using weighted exponential decay.
        
            High-priority factors (1-3) weighted 3x, medium (4-6) weighted 2x,
            low (7+) weighted 1x. Applies exponential decay for time-based factors.
            """
            return sum(
                score * self._get_weight(priority) * self._time_decay(timestamp)
                for priority, (score, timestamp) in factors.items()
            )
        ```
    
    ## Code Style
    
    ### Imports
    - **Location**: All imports at top of file
    - **Order**: Standard library → Third party → Local modules
    - **Format**: Absolute imports only (no relative imports)
    - **NO inline imports** except for circular dependency resolution
    
        ```python
        # ✅ GOOD
        import json
        from pathlib import Path
        
        from fastapi import FastAPI
        from pydantic import BaseModel
        
        from src.auth import authenticate_user
        from src.models import User
        
        # ❌ BAD
        def some_function():
            from src.other import helper  # Inline import
        ```
    
    ### Naming Conventions
    - **Functions/Variables**: `snake_case`
    - **Classes**: `PascalCase`
    - **Constants**: `UPPER_SNAKE_CASE`
    - **Private members**: `_leading_underscore`
    - **Files**: `snake_case.py`
    
    ### Nesting
    - **Maximum nesting depth**: 3 levels
    - Use early returns to reduce nesting
    - Extract nested logic to helper functions
    
        ```python
        # ✅ GOOD: Early return reduces nesting
        def process_user(user: User) -> ProcessResult:
            if not user.is_active:
                return ProcessResult(success=False, reason="inactive")
        
            if not user.has_permission("write"):
                return ProcessResult(success=False, reason="no_permission")
        
            return self._perform_operation(user)
        
        # ❌ BAD: Deep nesting
        def process_user(user: User) -> ProcessResult:
            if user.is_active:
                if user.has_permission("write"):
                    return self._perform_operation(user)
                else:
                    return ProcessResult(success=False, reason="no_permission")
            else:
                return ProcessResult(success=False, reason="inactive")
        ```
    
    ## Type Hints
    
    ### Requirements
    - **Full typing**: Every parameter and return value must have type hints
    - **Type syntax**: Use modern syntax (`str | None` not `Optional[str]`)
    - **Avoid `Any`**: Use specific types or protocols instead
    
        ```python
        # ✅ GOOD
        def fetch_user(user_id: str) -> User | None:
            pass
        
        def process_items(items: list[dict[str, Any]]) -> dict[str, int]:
            pass
        
        # ❌ BAD
        def fetch_user(user_id):  # Missing type hints
            pass
        
        def process_items(items: Any) -> Any:  # Too vague
            pass
        ```
    
    ## Python-Specific Rules
    
    ### Async/Await
    - **Required for all I/O operations**: Database queries, API calls, file I/O
    - Use `async def` for async functions
    - Use `await` for async calls (never `.result()` or blocking)
    
    ### Models
    - Use Pydantic v2 for data models
    - Inherit from `BaseModel` or project-specific base classes
    - Validate data at boundaries (API inputs, external data)
    
    ### Architecture
    - **Service layer separation**: Business logic in services, not routes/endpoints
    - **No business logic in controllers**: Controllers orchestrate, services execute
    - **Dependency injection**: Use framework DI patterns
    
    ## Testing Standards
    
    ### Test Structure
    - **Framework**: pytest + pytest-mock
    - **File naming**: `test_*.py`
    - **Test naming**: `test_<function>_<scenario>`
    - **Location**: Mirror source structure in `tests/` directory
    
        ```text
        src/auth.py       →  tests/unit/src/test_auth.py
        src/models/user.py → tests/unit/src/models/test_user.py
        ```
    
    ### Test Requirements
    - **Coverage**: Minimum 80% code coverage
    - **Test types**: Unit (isolated), Integration (with dependencies), E2E (full workflow)
    - **Assertions**: One logical assertion per test (can have multiple `assert` statements if related)
    
    ### Test Documentation
    - **Test docstrings**: NOT required (test names should be descriptive)
    - **Comments in tests**: Use for complex setup or non-obvious assertions
    
    ## Static Analysis
    
    ### Type Checking
    - **Tool**: MyPy
    - **Requirement**: Zero type errors before commit
    - **Config**: Use project's `mypy.ini` or `pyproject.toml` settings
    
    ### Linting
    - **Tool**: Ruff
    - **Requirement**: Zero linting errors before commit
    - **Config**: Use project's `ruff.toml` or `pyproject.toml` settings
    
    ## Commit Requirements
    
    Before committing code:
    - [ ] All tests pass
    - [ ] MyPy reports zero errors
    - [ ] Ruff reports zero issues
    - [ ] Code coverage ≥ 80%
    - [ ] No obvious docstrings or comments added
    - [ ] All imports at file top
    - [ ] Functions have clear, self-documenting names
    
    ## Exceptions and Overrides
    
    If you need to deviate from these standards:
    - Document the reason in a code comment
    - Note the deviation in your commit message
    - Keep deviations minimal and justified
    ```

## Customization Instructions

To customize this template for your project:

1. Copy this template to `.respec-ai/coding-standards.md` in your project workspace
2. Modify sections to match your team's preferences
3. Add project-specific rules (framework conventions, domain-specific patterns)
4. Remove sections that don't apply to your project
5. Add examples relevant to your codebase

The `build-coder` agent will read this file and apply all rules to generated code.
