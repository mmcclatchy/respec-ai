# `respec-ai`

---

> **⚠️ Active Development:** `respec-ai` is under active development.
> - All core workflows are functional:
>   - `/respec-plan` - Strategic planning with conversational discovery
>   - `/respec-roadmap` - Multi-phase implementation roadmap
>   - `/respec-phase` - Technical specifications with architecture decisions
>   - `/respec-task` - Detailed task breakdowns from phases
>   - `/respec-code` - TDD-driven implementation with code review
> - Specialized coding agents (frontend, backend, database) are planned enhancements.

---

**Agentic Reflection-Driven Development Platform for Claude Code**

Using LLMs for development requires critical evaluation—you can't just trust the output. But manually checking if generated content matches your intent is frustrating and feels like spinning tires. Writing specifications helps keep LLMs on track, but maintaining them during development becomes more time-consuming than generating code. Overlapping responsibilities across documents create sync hell. Developers end up spending more time iterating with LLMs and syncing documents than actually building.

`respec-ai` is a meta MCP server for Claude Code that automates critical evaluation through **agentic reflection loops**. Producer agents (plan-analyst, phase-architect, task-planner, coder) generate content while specialized critic agents (plan-critic, phase-critic, task-critic, code-reviewer) autonomously evaluate, score, and provide feedback until 0-100 quality thresholds are met. The system follows standard enterprise workflow (PM → Architect → Senior Eng → Dev) with clear separation of responsibilities at each stage—Plan, Roadmap, Phase, Task, Code. You determine the target, agents iteratively refine through producer-critic cycles, and the system only escalates to you when autonomous improvement plateaus—removing 60-70% of manual iteration burden. Works with Linear, GitHub, or local Markdown files.

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

That's it! `respec-ai` will guide you through strategic planning, technical phases, and implementation.

**[Full Installation Guide →](docs/CLI_GUIDE.md#installation)**

## Key Features

- **Platform Abstraction** - Work with Linear, GitHub, or Markdown files through a unified interface. Switch platforms without changing workflows.

- **Agentic Reflection Loops** - Producer-critic agent pairs (plan-analyst ↔ plan-critic, phase-architect ↔ phase-critic, task-planner ↔ task-critic, coder ↔ code-reviewer) autonomously iterate through refinement cycles. Critics score quality 0-100 and provide actionable feedback, triggering automatic refinement until thresholds met or escalating to human review when improvement plateaus.

- **Hierarchical Validation** - Each level validates against the level above (code → task → phase → roadmap → plan) to prevent alignment drift. Every line of code traces back to business objectives through systematic validation.

- **Intelligent Escalation** - System detects when autonomous refinement plateaus and automatically escalates to human review with contextual feedback summaries, eliminating 75% of unnecessary manual intervention while preserving human judgment for ambiguous requirements.

- **Strategic to Implementation Pipeline** - Complete workflow from business objectives (`/respec-plan`) through phased roadmaps (`/respec-roadmap`), technical design (`/respec-phase`), task breakdown (`/respec-task`), to code generation (`/respec-code`).

- **Docker-Based MCP Server** - Containerized deployment with 38 MCP tools across 7 modules. Optional PostgreSQL persistence for multi-project workflows.

- **Type-Safe Architecture** - Enterprise-grade platform orchestrator with strategy pattern, Pydantic models, and comprehensive validation (595 tests passing).

## Platform Options

| Platform    | Best For              | Integration | Real-time |
|-------------|-----------------------|-------------|-----------|
| **Linear**  | Teams using Linear    | Full API    | ✅        |
| **GitHub**  | Open source projects  | Full API    | ❌        |
| **Markdown**| Solo developers       | Local files | ❌        |

**[Platform Comparison Guide →](docs/CLI_GUIDE.md#platform-selection)**

## Workflow Overview

**See [Workflow Guide →](docs/WORKFLOWS.md) for detailed workflow documentation.**

`respec-ai` provides a complete development pipeline with hierarchical validation at each stage:

```text
1. Strategic Planning
   /respec-plan
   → Conversational requirements gathering (plan-analyst)
   → Business objectives extraction
   → Quality validation with plan-critic (autonomous refinement loops)

2. Phase Breakdown
   /respec-roadmap
   → Multi-phase implementation roadmap (roadmap agent)
   → Initial phase documents for each phase
   → Refinement with roadmap-critic (validates against plan)

3. Technical Design
   /respec-phase [phase-name]
   → Detailed technical specifications (phase-architect)
   → Architecture and technology decisions
   → Quality loops with phase-critic (validates against roadmap)

4. Task Breakdown
   /respec-task [plan-name] [phase-name]
   → Detailed implementation task planning (task-planner)
   → Step-by-step development roadmap
   → Refinement with task-critic (validates against phase)

5. Implementation
   /respec-code [plan-name] [phase-name]
   → TDD-driven code generation (coder)
   → Test-first implementation
   → Code review with code-reviewer (validates against task breakdown)
```

Each stage uses **autonomous agentic reflection loops** where producer-critic pairs iteratively refine until quality thresholds met. Hierarchical validation ensures every code change traces back to business objectives.

```text
Producer Agent → Generate Content → Critic Agent → Score (0-100) → Decision
     ↑                                                                 ↓
     └─ Autonomous Refinement ←─ "refine" ←──────────────────┬────────┘
                                                              │
                                                         "complete" → Proceed
                                                              │
                                                    "user_input" → Escalate to Human
                                                         (stagnation detected)
```

## Documentation

- **[CLI Guide](docs/CLI_GUIDE.md)** - Installation, setup, CLI reference, configuration, troubleshooting
- **[Workflows Guide](docs/WORKFLOWS.md)** - Detailed workflow documentation, examples, best practices, technical details
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design, platform orchestrator, MCP tools, document models

## Plan Status

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
- ✅ Comprehensive test suite (595 passing tests)
- ✅ Plan workflow with agentic reflection loops
- ✅ Roadmap workflow with phase breakdown
- ✅ Phase workflow with technical specifications
- ✅ Task workflow with implementation planning
- ✅ Code workflow with TDD-driven implementation and review

### In Progress
- 🚧 Refinements and enhancements based on production usage

### Planned Enhancements
- 🔮 Specialized coding agents (frontend, backend, database, infrastructure reviewers)
- 🔮 Support for Cursor and OpenCode IDEs
- 🔮 Advanced analytics and reporting dashboards
- 🔮 Multi-language support beyond Python

## Requirements

- **Claude Code CLI** - For MCP server integration
- **Python 3.11+** - Runtime environment
- **Docker/Docker Desktop** - For containerized deployments
- **uv** - Package and version manager
- **Platform MCP Server** - Linear or GitHub (optional, for external platforms)

## License

No License

## Support

- [**CLI_GUIDE.md**](docs/CLI_GUIDE.md)
- **Issues:** [GitHub Issues](https://github.com/mmcclatchy/respec-ai/issues)
