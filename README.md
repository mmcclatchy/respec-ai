# RespecAI Workflow System

AI-powered specification-driven development workflow for Claude Code.

## What is RespecAI?

RespecAI is a **meta MCP server** that generates platform-specific workflow automation tools for AI-driven development. It creates custom Claude Code commands and agents tailored to your project management platform (Linear, GitHub, or local Markdown files).

### Key Features

- **Platform abstraction** - Work with Linear, GitHub, or Markdown seamlessly
- **Quality-driven workflows** - Automated refinement loops with critic agents
- **Strategic to implementation** - Plan → Roadmap → Spec → Build
- **Type-safe integration** - Platform-specific tools properly configured

## Quick Start

RespecAI installation has two parts:
1. **One-time MCP server setup** (configure RespecAI globally)
2. **Per-project setup** (generate workflow files for each project)

### 1. MCP Server Setup (One-Time)

Configure RespecAI as an MCP server in Claude Code:

**Step 1: Clone RespecAI repository**
```bash
# Clone to a permanent location
cd ~/coding/projects  # or your preferred location
git clone git@github.com:mmcclatchy/respec-ai.git
cd respec-ai
uv sync  # Install dependencies
```

**Step 2: Add to Claude Code configuration**

Edit `~/.claude/config.json` and add:

```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "uv",
      "args": ["run", "respec-server"],
      "cwd": "/absolute/path/to/respec-ai"
    }
  }
}
```

> **Important**: Replace `/absolute/path/to/respec-ai` with your actual path from Step 1. Use absolute paths, not `~` or relative paths.

**Step 3: Verify setup**

```bash
claude
```

Then in Claude Code:
```text
/mcp list
```

Expected output should include "respec-ai" with 32 tools available.

### 2. Project Setup (Per-Project)

Once the MCP server is configured, set up any project:

**Local installation:**
```bash
cd /path/to/your/project
~/coding/projects/respec-ai/scripts/install-respec-ai.sh -n myproject -p linear
# Choose platform: linear, github, or markdown
claude  # Restart to load commands
```

Then in Claude Code:
```text
/respec-plan  # Start your first workflow
```

**Remote installation (public repos only):**

> **⚠️ Important**: Remote installation only works for **public repositories**. For private repos, use local installation above.

```bash
cd /path/to/your/project
curl -fsSL https://raw.githubusercontent.com/mmcclatchy/respec-ai/main/scripts/install-respec-ai.sh | bash -s -- -n myproject -p linear --respec-path ~/coding/projects/respec-ai
claude  # Restart to load commands
```

Then in Claude Code:
```text
/respec-plan  # Start your first workflow
```

### 3. Start Using

```text
/respec-plan          # Create strategic plan
/respec-roadmap       # Break down into phases
/respec-spec          # Design specifications
/respec-build         # Implement features
```

**For complete installation instructions**, see [User Guide](docs/USER_GUIDE.md)

## Platform Options

| Platform | Best For | Integration | Real-time |
|----------|----------|-------------|-----------|
| **Linear** | Teams using Linear | Full API | ✅ |
| **GitHub** | Open source projects | Full API | ❌ |
| **Markdown** | Solo developers | Local files | ❌ |

## Documentation

### Getting Started
- **[User Guide](docs/USER_GUIDE.md)** - Complete usage documentation
  - Installation methods
  - Platform selection guide
  - Command reference
  - Workflow examples
  - Best practices
  - Troubleshooting

### Architecture & Development
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and implementation
  - Platform orchestrator (11-file system)
  - Template engine and strategy pattern
  - MCP tools (32 tools across 8 modules)
  - Document models and parsing
  - Deployment architecture

- **[Architecture Analysis](docs/ARCHITECTURE_ANALYSIS.md)** - Technical deep dive
  - Implementation quality assessment
  - Component analysis
  - Design pattern evaluation
  - Type safety framework
  - Testing and validation
  - Extensibility guide

- **[Architectural Realignment](docs/ARCHITECTURAL_REALIGNMENT.md)** - Development history
  - Implementation sessions
  - Technical decisions
  - Refactoring achievements
  - Production readiness status

## Requirements

### For All Users
- **Claude Code CLI** installed and configured
- **Platform MCP Server** (Linear or GitHub) if using external platforms

### For Local Installation
- **uv** (Python version and package manager)
- **Python 3.13+**
- **Unix-like OS** (Linux, macOS, Windows Subsystem for Linux)

### For Containerized Deployments
- **Docker** (Linux)
- **Docker Desktop** (macOS, Windows, Windows Subsystem for Linux)

## Workflow Overview

```text
1. Strategic Planning
   /respec-plan
   → Conversational requirements gathering
   → Creates strategic plan with business objectives
   → Quality validation with plan-critic

2. Phase Breakdown
   /respec-roadmap
   → Breaks plan into implementation phases
   → Creates initial specs for each phase
   → Quality refinement with roadmap-critic

3. Technical Design
   /respec-spec [spec-name]
   → Detailed technical specifications
   → Architecture and implementation approach
   → Quality refinement with spec-critic

4. Implementation
   /respec-build [spec-name]
   → Implementation planning
   → Code generation
   → Quality review with build-critic and build-reviewer
```

## Available Commands

- **`/respec-plan [project-name]`** - Create strategic project plans
- **`/respec-roadmap [project-name]`** - Generate multi-phase implementation roadmaps
- **`/respec-spec [spec-name]`** - Convert plans to detailed specifications
- **`/respec-build [spec-name]`** - Implement specifications with code
- **`/respec-plan-conversation`** - Convert conversations into structured plans

## Contributing

This is a production-ready system with enterprise-grade architecture. Contributions are welcome!

### Areas for Contribution
- Additional platform integrations (Jira, GitLab, Azure DevOps)
- Advanced analytics and reporting
- Cross-platform spec migration tools
- Documentation improvements
- Bug fixes and optimizations

## License

[Add License Information]

## Support

- **Issues**: [GitHub Issues](https://github.com/mmcclatchy/respec-ai/issues)
- **Documentation**: See [docs/](docs/) directory
- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## Project Status

🚧 **In Development** - Core platform system complete (516 tests passing), agent templates and end-to-end workflows still in progress

### Completed
- ✅ Platform orchestrator (11-file system)
- ✅ MCP tools (32 tools across 8 modules)
- ✅ Document models with markdown parsing
- ✅ Template generation system
- ✅ Installation and setup workflows
- ✅ Unit and integration tests
- ✅ Global MCP server architecture (single instance for all projects)

### In Progress
- 🚧 Agent template completion (some agents not yet implemented)
- 🚧 End-to-end workflow testing
- 🚧 Platform integration validation
- 🚧 User acceptance testing
- 🚧 **Multi-project isolation** (v1.1) - File-based state persistence and complete project isolation

### Multi-Project Support

**Current Status**: Works with limitations (see [Multi-Project Support in User Guide](docs/USER_GUIDE.md#multi-project-support))

- ✅ Multiple projects can use same MCP server
- ✅ Per-project configuration and commands
- ⚠️ State isolation in development (v1.1)

**Planned (v1.1)**: Complete multi-project isolation with file-based state persistence. See [MULTI_PROJECT_DESIGN.md](docs/MULTI_PROJECT_DESIGN.md) for architecture details.
