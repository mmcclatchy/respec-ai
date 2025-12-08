# `respec-ai`

---

> **⚠️ Active Development:** `respec-ai` is under active development.
> - Currently functional workflows:
>   - `/respec-plan`
>   - `/respec-roadmap`
>   - `/respec-spec`.
> - The `/respec-build` workflow is not yet functional.

---

**Agentic-Critic Refinement Loop Platform for Claude Code**

Using LLMs for development requires critical evaluation—you can't just trust the output. But manually checking if generated content matches your intent is frustrating and feels like spinning tires. Writing specs helps keep LLMs on track, but maintaining them during development becomes more time-consuming than generating code. Overlapping responsibilities across documents create sync hell. Developers end up spending more time iterating with LLMs and syncing documents than actually building.

`respec-ai` is a meta MCP server for Claude Code that adds systematic critical evaluation to LLM-generated content. Follows standard enterprise workflow (PM → Architect → Senior Eng → Dev) with clear separation of responsibilities at each stage—Plan, Roadmap, Spec, Build. Automated critic agents validate each stage against its parent document target using 0-100 quality thresholds. You determine the target, LLMs generate content, critics evaluate against parent specifications, and the system iterates until quality thresholds are met—removing the manual evaluation burden from developers. Works with Linear, GitHub, or local Markdown files.

---

## Quick Start

Get up and running in 3 steps:

```bash
# 1. Install respec-ai
uv tool install respec-ai  # Preferred (much faster)
# OR
brew tap mmcclatchy/respec-ai
brew install respec-ai

# 2. Initialize in your project
cd /path/to/your/project
respec-ai init -p markdown

# 3. Restart Claude Code and start planning
claude
/respec-plan my-first-project
```

That's it! `respec-ai` will guide you through strategic planning, technical specs, and implementation.

**[Full Installation Guide →](docs/CLI_GUIDE.md#installation)**

## Key Features

- **Platform Abstraction** - Work with Linear, GitHub, or Markdown files through a unified interface. Switch platforms without changing workflows.

- **Critic Refinement Loops** - Automated quality gates at each stage (0-100 thresholds) that serve triple duty: quality gatekeepers enforcing standards, alignment validators checking against parent documents, and improvement guides providing specific recommendations.

- **Hierarchical Validation** - Each level validates against the level above (code → spec → roadmap → plan) to prevent alignment drift. Every line of code traces back to business objectives through systematic validation.

- **Strategic to Implementation Pipeline** - Complete workflow from business objectives (`/respec-plan`) through phased roadmaps (`/respec-roadmap`), technical design (`/respec-spec`), to code generation (`/respec-build`).

- **Docker-Based MCP Server** - Containerized deployment with 38 MCP tools across 7 modules. Optional PostgreSQL persistence for multi-project workflows.

- **Type-Safe Architecture** - Enterprise-grade platform orchestrator with strategy pattern, Pydantic models, and comprehensive validation (595 tests passing).

## Platform Options

| Platform | Best For | Integration | Real-time |
|----------|----------|-------------|-----------|
| **Linear** | Teams using Linear | Full API | ✅ |
| **GitHub** | Open source projects | Full API | ❌ |
| **Markdown** | Solo developers | Local files | ❌ |

**[Platform Comparison Guide →](docs/CLI_GUIDE.md#platform-selection)**

## Workflow Overview

**See [Workflow Guide →](docs/WORKFLOWS.md) for detailed workflow documentation.**

`respec-ai` provides a complete development pipeline with hierarchical validation at each stage:

```text
1. Strategic Planning
   /respec-plan
   → Conversational requirements gathering
   → Business objectives extraction
   → Quality validation with plan-critic

2. Phase Breakdown
   /respec-roadmap
   → Multi-phase implementation roadmap
   → Initial specs for each phase
   → Refinement with roadmap-critic (validates against plan)

3. Technical Design
   /respec-spec [spec-name]
   → Detailed technical specifications
   → Architecture and technology decisions
   → Quality loops with spec-critic (validates against roadmap)

4. Implementation
   /respec-build [spec-name]
   → Implementation planning
   → TDD-driven code generation
   → Code review with build-reviewer (validates against spec)
```

Each stage iterates through refinement loops until quality threshold met or user approves. Hierarchical validation ensures every code change traces back to business objectives.

```text
Producer Agent → LLM Generation → Critic Agent → Score → MCP Decision
     ↑                                                     ↓
     └────── Refinement Loop ←─── "refine" ←───────────────┴────→ "complete" ──→ Proceed
```

## Documentation

- **[CLI Guide](docs/CLI_GUIDE.md)** - Installation, setup, CLI reference, configuration, troubleshooting
- **[Workflows Guide](docs/WORKFLOWS.md)** - Detailed workflow documentation, examples, best practices, technical details
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design, platform orchestrator, MCP tools, document models

## Project Status

**Version:** 0.6.3 (Beta)
**Test Coverage:** 595 passing tests
**MCP Tools:** 38 tools across 7 modules
**Maturity:** Production-ready core, beta workflows

### Completed
- ✅ Platform orchestrator (11-file system)
- ✅ MCP server with 38 tools
- ✅ Document models with markdown parsing
- ✅ Template generation system
- ✅ Docker deployment (dev and production)
- ✅ CLI with 13 commands
- ✅ Comprehensive test suite

### In Progress
- 🚧 Build/Code Workflow

### Planned Features
- 🚧 Add specialized coding and critic subagents (frontend, backend, database, etc.)
- 🚧 Add support for Cursor and OpenCode
- 🚧 Advanced analytics and reporting

## Requirements

- **Claude Code CLI** - For MCP server integration
- **Python 3.11+** - Runtime environment
- **Docker/Docker Desktop** - For containerized deployments
- **uv** - Package and version manager
- **Platform MCP Server** - Linear or GitHub (optional, for external platforms)

## License

MIT License

## Support

- [**CLI_GUIDE.md**](docs/CLI_GUIDE.md)
- **Issues:** [GitHub Issues](https://github.com/mmcclatchy/respec-ai/issues)
