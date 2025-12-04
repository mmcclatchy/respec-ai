# SpecAI MCP Server - Project Standards

## Project Rules (Mandatory)

### Critical Requirements

- **No test logic in production** - Keep test code completely separate
- **Minimal comments** - Code should be self-documenting through clear naming and structure
- **Docstrings ONLY for**:
  - Public API interfaces exposed to other services
  - MCP tools that will be called by external agents
  - Complex algorithms where the "why" isn't obvious from the code
  - **NOT for**: Obvious getters, simple CRUD operations, basic parameter mapping
- **Comments ONLY for**:
  - Non-obvious business logic or algorithms
  - Complex mathematical operations
  - Regulatory/compliance requirements
  - **NEVER for**: Variable declarations, simple function calls, obvious operations
- **No global variables** (except `UPPER_CASE` constants)
- **Minimal nesting** - Max 3 levels deep
- **No inline imports** - All imports at file top (except circular dependency resolution)
- **Languages**: Python only

### Examples of VIOLATIONS

```python
# ❌ WRONG: Obvious docstring
def get_user_name(self) -> str:
    """Get the user name."""
    return self.name

# ❌ WRONG: Obvious comment  
user_name = get_user_name()  # Get the user name

# ❌ WRONG: Inline import
def some_function():
    from services.other import helper  # ❌ Move to top

# ✅ CORRECT: No unnecessary documentation
def get_user_name(self) -> str:
    return self.name

# ✅ CORRECT: Complex logic documented
def calculate_weighted_quality_score(self, gates: dict[str, float]) -> float:
    """Calculate FSDD quality score using exponential weighting.
    
    Critical gates (1-4) weighted 2x, others weighted 1x.
    Threshold: 0.85 required for quality gate passage.
    """
    return sum(score * (2.0 if i <= 4 else 1.0) for i, score in enumerate(gates.values()))
```

### Python Standards

- **Virtual environment**: Use `uv` for all Python operations
- **Imports**: Absolute imports at file top
- **Async/await**: Required for all I/O operations
- **Full typing**: Every parameter and return value typed
- **Type syntax**: `str | None` (never `str | None`)
- **Models**: Use Pydantic v2 (`BestPracticeModel`)
- **Architecture**: Service layer separate from endpoints
- **Testing**: pytest + pytest-mock only

### Enforcement

**MANDATORY COMPLIANCE**: These rules override all global guidelines and defaults.

**Immediate Correction Required**: Any violation must be fixed before proceeding with other work.

**No Exceptions Without Authorization**: These standards apply to ALL code - services, tests, utilities, scripts.

**Self-Review Checklist Before Submitting**:
- [ ] No obvious docstrings or comments
- [ ] All imports at top of file  
- [ ] No inline imports
- [ ] Functions/variables have clear, self-documenting names
- [ ] Complex logic (and only complex logic) is documented

## Development Workflow

### Before Coding

1. Review relevant documentation
2. Check existing patterns in codebase
3. Plan service layer separation

### Code Structure

```text
services/             # Business logic
services/models/      # Pydantic models
tests/unit/           # pytest unit tests
tests/integration/    # pytest integration tests
tests/e2e/            # pytest end-to-end tests
```

### Quality Gates

- All endpoints delegate to services
- All functions fully typed
- No business logic in routes
- Tests cover service layer
