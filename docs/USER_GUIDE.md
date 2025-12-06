# RespecAI User Guide

Complete guide to using RespecAI for AI-driven specification-based development.

## What is RespecAI?

RespecAI is a **meta MCP server** that generates platform-specific workflow tools for AI-driven development. It creates custom Claude Code commands and agents tailored to your project management platform (Linear, GitHub, or local Markdown files).

### Key Benefits

- **Platform flexibility** - Work with Linear issues, GitHub issues, or local Markdown files
- **Automated setup** - Generate complete workflow tools with a single command
- **Type-safe integration** - Platform-specific tools properly configured for your environment
- **Refinement loops** - Quality-driven development with critic agents and iterative improvement

### Current Status

**MVP Complete** - RespecAI is ready for real-world usage:
- ✅ MCP server fully functional
- ✅ Multi-project architecture implemented (Phase 1)
- ✅ All 29+ tools operational
- ✅ 391 tests passing
- ✅ Installation and setup validated

See [SETUP_IMPROVEMENTS.md](SETUP_IMPROVEMENTS.md) for implementation status and [MULTI_PROJECT_DESIGN.md](MULTI_PROJECT_DESIGN.md) for architecture details.

## Table of Contents

- [What is RespecAI?](#what-is-respecai)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation Overview](#installation-overview)
  - [Part 1: RespecAI Package Installation](#part-1-respecai-package-installation-one-time)
  - [Part 2: Project Setup](#part-2-project-setup-per-project)
  - [Quick Start: Your First RespecAI Workflow](#quick-start-your-first-respecai-workflow)
- [Multi-Project Support](#multi-project-support)
- [CLI Reference](#cli-reference)
  - [respec-ai init](#respec-ai-init)
  - [respec-ai platform](#respec-ai-platform)
  - [respec-ai status](#respec-ai-status)
  - [respec-ai validate](#respec-ai-validate)
  - [respec-ai upgrade](#respec-ai-upgrade)
  - [respec-ai register-mcp](#respec-ai-register-mcp)
- [Platform Selection](#platform-selection)
- [Available Commands](#available-commands)
  - [/respec-plan](#respec-plan)
  - [/respec-roadmap](#respec-roadmap)
  - [/respec-spec](#respec-spec)
  - [/respec-build](#respec-build)
- [Workflow Examples](#workflow-examples)
- [Quality & Refinement Loops](#quality--refinement-loops)
- [Platform-Specific Workflows](#platform-specific-workflows)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
  - [RespecAI MCP Server Not Available](#respecai-mcp-server-not-available)
  - [Commands Not Found](#commands-not-found)
  - [Homebrew Installation Issues](#homebrew-installation-issues)
- [Best Practices](#best-practices)
- [Advanced Usage](#advanced-usage)
- [Local Development Setup](#local-development-setup)
  - [Prerequisites](#prerequisites-1)
  - [Quick Setup (Recommended)](#quick-setup-recommended)
  - [Alternative: Manual Configuration](#alternative-manual-configuration)
  - [Choosing a State Manager](#choosing-a-state-manager)
  - [Development Workflows](#development-workflows)
  - [Troubleshooting Local Development](#troubleshooting-local-development)
- [Getting Help](#getting-help)
- [Next Steps](#next-steps)

## Getting Started

### Prerequisites

**Required for all users:**
- **Claude Code CLI** installed and configured
- **Git** for repository access

**For RespecAI installation (choose one method):**

**Option A: Homebrew (macOS only):**
- **macOS** operating system
- **Homebrew** package manager
- **Docker Desktop** (required for MCP server functionality)

**Option B: uv Tool (all platforms):**
- **uv** (Python version and package manager) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Python 3.11+**
- **Unix-like operating system** (Linux, macOS, or Windows Subsystem for Linux)
- **Docker** (Linux) or **Docker Desktop** (macOS, Windows, WSL)

**For platform integrations (optional):**
- **Linear MCP Server** - If using Linear platform
- **GitHub MCP Server** - If using GitHub platform
- **Markdown platform** - No additional requirements (uses local files)

### Installation Overview

RespecAI installation has two parts:

1. **RespecAI Package Installation** (one-time) - Install the respec-ai package from PyPI
2. **Project Initialization** (per-project) - Initialize RespecAI in your projects

Both parts can be completed with a single command.

### Part 1: RespecAI Package Installation (One-Time)

This installs the RespecAI package and makes the CLI available globally.

Choose the installation method that best fits your platform:

#### Option A: Homebrew Installation (macOS - Recommended)

⚠️ **Development Version**: Currently installing from TestPyPI for testing. Production release coming soon.

**Prerequisites:**
- macOS with Homebrew installed
- Docker Desktop (required for MCP server functionality)

**Installation:**
```bash
# Add the development tap
brew tap mmcclatchy/respec-ai

# Install respec-ai
brew install respec-ai

# Verify installation
respec-ai --version
```

**Expected output:**
```text
respec-ai 0.5.15
```

**What gets installed:**
- ✅ respec-ai CLI tool
- ✅ All Python dependencies (pydantic, rich, docker, etc.)
- ✅ Isolated virtualenv (no conflicts with system Python)

**Note:** The MCP server will be automatically registered in Step 2 or can be registered manually.

#### Option B: uv Tool Installation (All Platforms)

**Prerequisites:**
- uv installed ([Install uv](https://docs.astral.sh/uv/getting-started/installation/))
- Python 3.11+
- Docker or Docker Desktop

**For development/testing (TestPyPI):**
```bash
# Install from TestPyPI
uv tool install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ respec-ai

# Verify installation
respec-ai --version
```

**For production (PyPI):**
```bash
# Install from PyPI (when available)
uv tool install respec-ai

# Verify installation
respec-ai --version
```

**Expected output:**
```text
respec-ai 0.5.15
```

**What gets installed:**
- ✅ respec-ai CLI tool in isolated environment
- ✅ All Python dependencies automatically
- ✅ Cross-platform compatibility

#### Step 2: Register MCP Server (Automatic or Manual)

The MCP server can be registered automatically during project initialization (recommended) or manually. **This step works the same regardless of which installation method you used** (Homebrew or uv tool).

**Option A: Automatic Registration (Recommended)**

The MCP server will be automatically registered when you run `respec-ai init` in your first project.

**Option B: Manual Registration**

If you prefer to register the MCP server separately (or if automatic registration was skipped):
```bash
respec-ai register-mcp
```

**Expected output:**
```text
RespecAI MCP server registered successfully
Package path: /path/to/installed/respec-ai
Restart Claude Code to activate the MCP server
```

#### Step 3: Verify Installation

**Restart Claude Code** to load the MCP server, then verify:

```bash
claude
```

In Claude Code, run:
```text
/mcp list
```

**Expected output should include:**
```text
Available MCP Servers:
  RespecAI
    ├─ 29+ tools available
    ├─ create_project_plan
    ├─ store_project_plan
    └─ [other tools...]
```

**✓ Success criteria:**
- RespecAI appears in the MCP server list
- Tool count shows 29+ tools
- No error messages

**If RespecAI doesn't appear**, see [Troubleshooting](#respecai-mcp-server-not-available) below.

---

### Part 2: Project Setup (Per-Project)

Initialize RespecAI in any project with a single command.

#### Initialize Your Project

**Step 1: Navigate to your project**
```bash
cd /path/to/your/project
```

**Step 2: Initialize RespecAI**
```bash
# Choose your platform: linear, github, or markdown
respec-ai init --platform linear

# Optional: specify project name (defaults to directory name)
respec-ai init --platform github --project-name my-project

# Optional: skip automatic MCP registration
respec-ai init --platform markdown --skip-mcp-registration
```

**What this creates:**
- `.claude/commands/` - 5 RespecAI workflow commands
- `.claude/agents/` - 12 RespecAI workflow agents
- `.respec-ai/config.json` - Platform configuration

**Expected output:**
```text
✅ RespecAI setup complete!

Setting              Value
Platform             linear
Files Created        17
Location             /path/to/project
MCP Server           ✓ Registered as RespecAI

Available Commands (restart Claude Code to activate):
  • /respec-plan - Create strategic plans
  • /respec-roadmap - Create phased roadmaps
  • /respec-spec - Transform plans into specs
  • /respec-build - Execute implementation

🚀 Ready to begin! Restart Claude Code to use the RespecAI commands.
```

**Step 3: Restart Claude Code**
```bash
# Exit and restart Claude Code to load new commands
claude
```

#### Verify Project Setup

Check that everything was created correctly:

```bash
# Verify installation
respec-ai status
```

**Expected output:**
```text
Project Configuration
Setting              Value
Project Path         /path/to/project
Platform             linear
Config Version       0.2.0
Package Version      0.2.0
MCP Server           RespecAI (✓ Registered)

Generated Files
Category            Count
Commands            5
Agents              12
```

**Verification checklist:**
- [ ] All 5 commands exist in `.claude/commands/`
- [ ] All 12 agents exist in `.claude/agents/`
- [ ] Platform configuration shows correct platform
- [ ] Commands autocomplete with `/respec-` in Claude Code
- [ ] RespecAI MCP server shows in `/mcp list`

**If verification fails**, see [Troubleshooting](#commands-not-found) below.

---

### Quick Start: Your First RespecAI Workflow

Now that setup is complete, try creating your first plan:

```bash
# In your project directory
claude
```

```text
# Start with strategic planning
/respec-plan

# Or if you want to create a multi-phase roadmap
/respec-roadmap my-project-name
```

Follow the interactive prompts to create your first strategic plan. See [Available Commands](#available-commands) below for detailed workflow documentation.

---

## Multi-Project Support

**Status**: ✅ MVP Complete (Phase 1)

### Current Implementation

RespecAI supports running multiple projects with explicit project context. Each project maintains its own:

- ✅ Platform configuration (`.respec-ai/config/platform.json`)
- ✅ Command templates (`.claude/commands/*.md`)
- ✅ Agent templates (`.claude/agents/*.md`)
- ✅ Explicit project context via `project_path` parameter
- ✅ Linear/GitHub issues (naturally isolated by workspace/repository)

**What This Means:**
- All 36+ MCP tools now accept explicit `project_path` parameter
- Multiple projects can use the same RespecAI MCP server
- Each project's workflows operate independently when project_path is specified
- No cross-project interference at the tool level

### Current Architecture

**What Works Now (Phase 1 Complete):**
- ✅ Tool-level multi-project support (explicit `project_path`)
- ✅ Different projects can use different platforms
- ✅ Simultaneous project usage (with proper project_path specification)
- ✅ All 404 tests passing with multi-project scenarios

**Current Limitations (Acceptable for MVP):**
- ⏸️ **In-memory state**: Plans, specs, and loop state stored in memory
  - State does not persist across MCP server restarts
  - Acceptable for single-user development workflows
- ⏸️ **Global configuration**: Platform config stored at `~/.respec-ai/projects/`
  - Works fine for solo development
  - Per-project config deferred until team collaboration features needed

### Recommended Usage (MVP)

**For single user / solo development**: Works perfectly with no limitations.

**For multiple projects**:
- ✅ Set up each project independently with `/init-respec-ai`
- ✅ Different projects can use different platforms
- ✅ Commands work correctly when project context is clear
- ⏸️ State resets on MCP server restart (acceptable for MVP)

### Future Enhancements (Post-MVP)

**Database Persistence** (planned, not file-based):
- Persistent state storage across server restarts
- Database-backed state management
- Enhanced multi-user support

**Per-Project Configuration** (when team collaboration needed):
- Move config from `~/.respec-ai/projects/` to `.respec-ai/config/`
- Repository-portable configuration
- Better team workflow support

**See [MULTI_PROJECT_DESIGN.md](MULTI_PROJECT_DESIGN.md) and [SETUP_IMPROVEMENTS.md](SETUP_IMPROVEMENTS.md) for:**
- Complete architecture details
- Phase 1 implementation (completed)
- Future enhancement roadmap
- Technical implementation notes

---

## CLI Reference

RespecAI provides a rich CLI for managing your workflow setup.

### `respec-ai init`

Initialize RespecAI in the current project.

**Usage:**
```bash
respec-ai init --platform <platform> [OPTIONS]
```

**Arguments:**
- `--platform` (required) - Platform type: `linear`, `github`, or `markdown`
- `--project-name` (optional) - Project name (defaults to directory name)
- `--skip-mcp-registration` (optional) - Skip automatic MCP server registration

**Examples:**
```bash
# Initialize with Linear platform
respec-ai init --platform linear

# Initialize with custom project name
respec-ai init --platform github --project-name my-app

# Initialize without MCP registration
respec-ai init --platform markdown --skip-mcp-registration
```

---

### `respec-ai platform`

Change platform and regenerate all templates.

**Usage:**
```bash
respec-ai platform <platform>
```

**Arguments:**
- `platform` (required) - New platform: `linear`, `github`, or `markdown`

**Example:**
```bash
# Switch from Linear to GitHub
respec-ai platform github
```

**Output:**
```text
Platform changed: linear → github
Regenerated 5 commands and 12 agents

⚠ Restart Claude Code to activate the updated templates
```

**Note:** Existing work (plans, specs) won't automatically migrate. You'll need to manually recreate them in the new platform.

---

### `respec-ai status`

Show project configuration and status.

**Usage:**
```bash
respec-ai status
```

**Output:**
```text
Project Configuration
Setting              Value
Project Path         /path/to/project
Platform             linear
Config Version       0.2.0
Package Version      0.2.0
MCP Server           RespecAI (✓ Registered)

Generated Files
Category            Count
Commands            5
Agents              12
```

---

### `respec-ai validate`

Validate project setup with comprehensive diagnostics.

**Usage:**
```bash
respec-ai validate
```

**Validation Checks:**
- Project initialized (config file exists)
- Config valid (proper JSON format)
- Platform valid (one of: linear, github, markdown)
- Version current (config matches package version)
- Commands directory (expected 5 files)
- Agents directory (expected 12 files)
- MCP registered (RespecAI server in Claude Code)

**Output (all passing):**
```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ All validation checks passed!                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Project: /path/to/project

Validation Results
Check                Status
Project Initialized  ✓ Config file exists
Config Valid         ✓ Config is valid JSON
Platform Valid       ✓ Platform: linear
Version Current      ✓ Version: 0.2.0
Commands Directory   ✓ 5 commands found
Agents Directory     ✓ 12 agents found
MCP Registered       ✓ RespecAI server registered
```

**Output (with failures):**
```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Some validation checks failed                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Project: /path/to/project

Validation Results
Check                Status
Project Initialized  ✗ Not initialized
Config Valid         ✗ Config missing
Platform Valid       ✗ Config missing
Version Current      ✗ Config missing
Commands Directory   ✗ Directory missing
Agents Directory     ✗ Directory missing
MCP Registered       ✗ Not registered in Claude Code

⚠ Run respec-ai init to fix missing files
```

---

### `respec-ai upgrade`

Update templates to the latest version.

**Usage:**
```bash
respec-ai upgrade [--force]
```

**Options:**
- `--force` (optional) - Regenerate templates even if version is current

**Example:**
```bash
# Standard upgrade
respec-ai upgrade

# Force regeneration
respec-ai upgrade --force
```

**Output:**
```text
Templates updated: 0.1.0 → 0.2.0
Regenerated 5 commands and 12 agents

⚠ Restart Claude Code to activate the updated templates
```

---

### `respec-ai register-mcp`

Manually register the RespecAI MCP server in Claude Code.

**Usage:**
```bash
respec-ai register-mcp [--force]
```

**Options:**
- `--force` (optional) - Re-register even if already registered

**Example:**
```bash
# Initial registration
respec-ai register-mcp

# Force re-registration
respec-ai register-mcp --force
```

**Output:**
```text
RespecAI MCP server registered successfully
Package path: /path/to/installed/respec-ai
Restart Claude Code to activate the MCP server
```

**When to use:**
- If automatic registration was skipped during `respec-ai init`
- If MCP server registration was corrupted
- If you need to update the registration after moving the package

---

### Global Options

**Version:**
```bash
respec-ai --version
```

**Help:**
```bash
respec-ai --help
respec-ai <command> --help
```

---

## Platform Selection

### Choosing Your Platform

RespecAI supports three platforms with different capabilities:

#### Linear Platform

**Best for:** Teams using Linear for project management

**Capabilities:**
- ✅ Issue tracking
- ✅ Projects
- ✅ Comments
- ✅ Labels
- ✅ Cycles (sprint planning)
- ✅ Real-time collaboration
- ✅ External integration

**Requirements:**
- Linear MCP server configured in Claude Code
- Linear API access

**Workflow:**
- Specs created as Linear issues
- Plans stored as Linear projects
- Comments for feedback and discussion

#### GitHub Platform

**Best for:** Teams using GitHub for project management

**Capabilities:**
- ✅ Issue tracking
- ✅ Projects (boards)
- ✅ Comments
- ✅ Labels
- ✅ Milestones
- ❌ Real-time collaboration
- ✅ External integration

**Requirements:**
- GitHub MCP server configured in Claude Code
- GitHub API access

**Workflow:**
- Specs created as GitHub issues
- Plans stored as GitHub project boards
- Comments for feedback

#### Markdown Platform

**Best for:** Solo developers or teams preferring local files

**Capabilities:**
- ✅ Issue tracking (via structured files)
- ✅ Projects (via markdown files)
- ✅ Comments (via markdown sections)
- ❌ Labels
- ❌ Real-time collaboration
- ❌ External integration

**Requirements:**
- None (uses built-in Claude Code tools)

**Workflow:**
- Specs stored as markdown files in `.respec-ai/projects/[project-name]/respec-specs/`
- Plans stored as markdown files
- Git-friendly version control

### Platform Recommendations

**Choose Linear if:**
- Your team uses Linear for project management
- You need real-time collaboration
- You want native Linear integration

**Choose GitHub if:**
- Your team uses GitHub issues
- You want project board integration
- You need milestone tracking

**Choose Markdown if:**
- You're working solo
- You prefer local files
- You want Git-based version control
- You don't need external platform integration

## Available Commands

### Understanding Command and Agent Templates

**Commands** (what you invoke with `/respec-*`) use `allowed-tools:` in their frontmatter:
```yaml
---
allowed-tools: {tools.tools_yaml}
argument-hint: [param-name]
description: Command description
---
```

**Agents** (invoked by commands) use `tools:` with comma-separated list:
```yaml
---
name: agent-name
description: Agent purpose
model: sonnet
tools: tool1, tool2, tool3
---
```

**Important Formatting Rules**:
- **Tools must be comma-separated on a single line** (not YAML array format with `-` prefix)
- Commands use variable interpolation `{tools.tools_yaml}` for platform-specific tools
- Agents list tools explicitly, separated by commas

**Note**: As a user, you don't interact with frontmatter directly. This formatting ensures commands and agents have proper tool access for your platform (Linear/GitHub/Markdown).

### `/respec-plan`

**Purpose:** Create strategic project plans through interactive discovery

**Workflow:**
1. Uses `/respec-plan-conversation` for natural language requirements gathering
2. Creates strategic plan document
3. Evaluates plan quality with plan-critic agent
4. Refines through iterative improvement loops
5. Extracts business objectives with plan-analyst agent
6. Validates extraction with analyst-critic agent

**When to use:**
- Starting a new project or feature
- Need to understand business objectives
- Want structured strategic planning

**Example:**
```text
User: /respec-plan

Claude: I'll help you create a strategic plan. Let me start by understanding your goals.

[Interactive conversation begins...]
```

### `/respec-plan-conversation`

**Purpose:** Interactive conversation for requirements gathering

**Workflow:**
1. Asks clarifying questions about project goals
2. Explores business objectives and constraints
3. Gathers context for strategic planning
4. Provides input for plan creation

**When to use:**
- This is not to be used by end-users
- This command is used as a subcommand of `/respec-plan`

### `/respec-roadmap`

**Purpose:** Generate multi-phase implementation roadmaps

**Workflow:**
1. Analyzes project scope and complexity
2. Creates phase-based implementation roadmap
3. Evaluates roadmap with roadmap-critic agent
4. Generates initial specifications for each phase
5. Refines through iterative improvement

**When to use:**
- Starting large, complex projects
- Need phase-based planning
- Want to break work into manageable chunks

**Example:**
```text
User: /respec-roadmap [project-name]

Claude: I'll create a multi-phase implementation roadmap.
[Generates roadmap with phases, milestones, and initial specs]
```

### `/respec-spec`

**Purpose:** Convert strategic plans into detailed technical specifications

**Workflow:**
1. Retrieves existing strategic plan
2. Creates technical specification using spec-architect agent
3. Evaluates spec quality with spec-critic agent
4. Refines through iterative improvement
5. Creates spec in your platform (Linear issue, GitHub issue, or Markdown file)

**When to use:**
- After completing strategic planning
- Need detailed technical specifications
- Ready to break down implementation approach

**Example:**
```text
User: /respec-spec [spec-name]

Claude: I'll create a technical specification from your strategic plan.
[Generates spec with technical details, architecture, and implementation approach]
```

### `/respec-build`

**Purpose:** Implement specifications with automated code generation

**Workflow:**
1. Retrieves technical specification
2. Creates build plan with build-planner agent
3. Evaluates plan with build-critic agent
4. Generates code with build-coder agent
5. Reviews code with build-reviewer agent
6. Refines through quality loops

**When to use:**
- After completing technical specifications
- Ready to implement features
- Want automated code generation with quality checks

**Example:**
```text
User: /respec-build [spec-name]

Claude: I'll implement the specification with automated code generation.
[Creates build plan, generates code, reviews quality]
```

## Workflow Examples

### Example 1: New Feature Development

**Scenario:** Adding user authentication to an application

```text
1. Strategic Planning:
   User: /respec-plan [project-name]
   [Interactive conversation about authentication needs]
   → Creates strategic plan with business objectives

2. Technical Specification:
   User: /respec-spec [spec-name]
   → Generates technical spec with architecture details
   → Creates Linear issue (or GitHub issue, or markdown file)

3. Implementation:
   User: /respec-build [spec-name]
   → Creates build plan with implementation steps
   → Generates authentication code
   → Reviews code quality
   → Implements feature
```

### Example 2: Large Project Roadmap

**Scenario:** Building a complete SaaS application

```text
1. Strategic Planning:
   User: /respec-plan [project-name]
   → Creates strategic plan for entire SaaS application
   → Defines business objectives and high-level requirements

2. Roadmap Creation:
   User: /respec-roadmap [project-name]
   → Breaks down strategic plan into implementation phases:
     - Phase 1: User authentication
     - Phase 2: Core features
     - Phase 3: Payment integration
     - Phase 4: Analytics dashboard
   → Creates initial specs for each phase automatically

3. Phase Implementation:
   For each phase/spec created by roadmap:
   User: /respec-spec [spec-name] (to elaborate technical details)
   User: /respec-build [spec-name] (to implement the phase)
```

### Example 3: Requirements Discovery

**Scenario:** Unclear project requirements

```text
1. Strategic Planning with Conversational Discovery:
   User: /respec-plan [project-name]
   Claude: (runs /respec-plan-conversation internally)
   Claude: What problem are you trying to solve?
   User: I want users to collaborate in real-time
   Claude: What kind of collaboration? Document editing? Chat? Screen sharing?
   [Conversation continues to clarify requirements]
   → Claude creates strategic plan based on conversation
   → Evaluates and refines plan through quality loops

2. Continue with roadmap or spec creation...
```

## Quality & Refinement Loops

RespecAI uses two types of quality loops:

### 1. Human-in-the-Loop with Quality Validation

**Used by:** `/respec-plan`

**Process:**
1. **Conversation:** `/respec-plan-conversation` conducts interactive Q&A to gather requirements
2. **Generation:** Creates strategic plan from conversation context
3. **Quality Check:** `plan-critic` evaluates the plan and provides quality score
4. **Human Review:** User sees quality score and decides: continue conversation, refine plan, or accept
5. **Analysis:** `plan-analyst` extracts structured business objectives
6. **Validation:** `analyst-critic` validates the extraction through MCP refinement loop
7. **Completion:** Final validated strategic plan

This is a **hybrid approach** - conversational gathering with automated quality validation and user decision points.

### 2. Automated Refinement Loops (MCP-Driven)

**Used by:** `/respec-roadmap`, `/respec-spec`, `/respec-build`

**Process:**
1. **Generation:** A generative agent creates content (roadmap, spec, build plan, code)
2. **Evaluation:** A critic agent scores quality (0-100)
3. **Decision:** MCP server determines next action:
   - **High score** → Proceed to next phase
   - **Improving score** → Refine with feedback
   - **Stagnation** → Request user input

### Critic Agents

**For Human-in-the-Loop (`/respec-plan`):**

**plan-critic:**
- Evaluates strategic plans after conversational gathering
- Provides quality score for user decision-making
- No automated refinement loop - user decides next action

**analyst-critic:**
- Validates business objective extraction
- Uses MCP-driven automated refinement loop
- Ensures completeness and accuracy of analysis

**For Automated Loops (`/respec-roadmap`, `/respec-spec`, `/respec-build`):**

**roadmap-critic:**
- Evaluates implementation roadmaps
- Checks phase breakdown and sizing
- Validates dependencies and ordering

**spec-critic:**
- Evaluates technical specifications
- Checks architecture design decisions
- Validates implementation approach

**build-critic:**
- Evaluates build plans
- Checks implementation steps
- Validates technology choices

**build-reviewer:**
- Reviews generated code
- Checks code quality and best practices
- Validates implementation correctness

### Quality Thresholds

Quality scores determine progression:

- **80-100:** Excellent quality, proceed
- **60-79:** Good quality, minor refinements
- **40-59:** Needs improvement, iterate
- **0-39:** Significant issues, major refinement

**Stagnation detection:**
- No improvement over successive iterations
- Max iterations reached (configurable)
- System requests user input

## Platform-Specific Workflows

### Linear Workflow

**Plan Storage:**
```text
1. /respec-plan creates strategic plan
2. Stored as Linear project
3. Issues linked to project
4. Cycles used for sprint planning
```

**Spec Creation:**
```text
1. /respec-spec creates Linear issue
2. Issue contains technical specification
3. Comments added for feedback
4. Labels applied for categorization
5. Project assigned for tracking
```

### GitHub Workflow

**Plan Storage:**
```text
1. /respec-plan creates strategic plan
2. Stored as GitHub project board
3. Issues linked to project
4. Milestones for phases
```

**Spec Creation:**
```text
1. /respec-spec creates GitHub issue
2. Issue contains technical specification
3. Comments for feedback
4. Labels for categorization
5. Milestone for tracking
```

### Markdown Workflow

**Plan Storage:**
```text
1. /respec-plan creates markdown file
2. Stored in .respec-ai/projects/[project-name]/project_plan.md
3. Structured sections
4. Git commit for history
```

**Spec Creation:**
```text
1. /respec-spec creates markdown file
2. Stored in .respec-ai/projects/[project-name]/respec-specs/
3. Structured markdown format
4. Git-friendly version control
5. Comments as markdown sections
```

## Configuration

### Platform Configuration

Platform selection stored in `.respec-ai/config/platform.json`:

```json
{
  "platform": "linear",
  "created_at": "2025-10-01T12:00:00.000000",
  "version": "1.0",
  "bootstrap": true
}
```

### Changing Platforms

To switch platforms in an existing project:

```bash
# Change to a different platform
respec-ai platform github

# Then restart Claude Code
claude
```

The command will:
- Update `.respec-ai/config.json` with new platform
- Regenerate all 5 commands in `.claude/commands/` with new platform-specific tools
- Regenerate all 12 agents in `.claude/agents/` with updated configurations

**Note:** Existing work (plans, specs) won't automatically migrate between platforms. You'll need to manually recreate them in the new platform if needed.

---

### Upgrading RespecAI

When a new version of RespecAI is released:

```bash
# Update the package
uv add respec-ai --upgrade

# Update your project templates
cd /path/to/your/project
respec-ai upgrade
```

This preserves your platform choice while updating templates to the latest version.

## Troubleshooting

### RespecAI MCP Server Not Available

**Problem:** RespecAI doesn't appear in `/mcp list` output

**Solution:**

1. **Verify RespecAI package is installed**
   ```bash
   respec-ai --version
   ```

   Should show: `respec-ai 0.2.0` (or current version)

   If command not found:
   ```bash
   uv add respec-ai
   # or for TestPyPI:
   uv add --index https://test.pypi.org/simple/ respec-ai
   ```

2. **Register MCP server**
   ```bash
   respec-ai register-mcp
   ```

3. **Verify registration**
   ```bash
   claude mcp list
   # Should show "RespecAI" in the list
   ```

4. **Restart Claude Code**
   ```bash
   claude
   /mcp list
   ```

**If still not working:**
- Re-register with force: `respec-ai register-mcp --force`
- Check Python version: `python --version` (must be 3.13+)
- Check uv installation: `uv --version`

---

### Platform MCP Server Not Found

**Problem:** Linear or GitHub MCP server not available (when using those platforms)

**Symptoms:**
- `/mcp list` doesn't show "linear-server" or "github"
- Platform-specific operations fail
- Error messages about missing Linear/GitHub tools

**Solution:**
```text
1. Check MCP server status:
   /mcp list

2. Install required MCP server:
   - Linear: Follow Linear MCP server setup documentation
   - GitHub: Follow GitHub MCP server setup documentation
   - Markdown: No external server required (uses local files)

3. Verify API access:
   - Linear: Check Linear API token is configured
   - GitHub: Check GitHub token is configured

4. Restart Claude Code after MCP server installation
```

---

### Commands Not Found

**Problem:** RespecAI commands don't appear or autocomplete

**Symptoms:**
- Typing `/respec-` doesn't autocomplete
- Error: "Command not found: /respec-plan"
- `.claude/commands/` directory is empty or missing files

**Solution:**

1. **Verify setup was completed**
   ```bash
   ls -la .claude/commands/respec-*.md
   ```

   Should show 5 files:
   - respec-plan.md
   - respec-roadmap.md
   - respec-spec.md
   - respec-build.md
   - respec-plan-conversation.md

2. **Check you're in the correct directory**
   ```bash
   pwd  # Should be your project directory
   ls .claude/  # Should exist
   ```

3. **If files are missing, re-run initialization**
   ```bash
   respec-ai init --platform [your-platform]
   # Then restart Claude Code
   ```

4. **Verify RespecAI MCP server is available**
   ```text
   /mcp list  # Should show "RespecAI"
   ```

   If RespecAI MCP server is missing, see [RespecAI MCP Server Not Available](#respecai-mcp-server-not-available) above.

5. **Check for file permissions issues**
   ```bash
   ls -la .claude/commands/
   # Files should be readable (not 000 permissions)

   # Fix if needed:
   chmod 644 .claude/commands/*.md
   ```

6. **Restart Claude Code to reload commands**
   ```bash
   # Exit Claude Code completely, then:
   cd /path/to/your/project
   claude
   ```

**If commands still don't appear:**
- Try creating `.claude/commands/` manually: `mkdir -p .claude/commands`
- Re-run initialization: `respec-ai init --platform [your-platform]`
- Check Claude Code version is up-to-date

---

### Platform Tools Not Working

**Problem:** Platform-specific operations fail during workflow execution

**Symptoms:**
- Error: "Tool not found" when creating issues/specs
- Linear/GitHub operations timeout or fail
- Markdown files not created in expected locations

**Solution:**

1. **Verify platform configuration**
   ```bash
   cat .respec-ai/config/platform.json
   ```

   Should show correct platform:
   ```json
   {
     "platform": "markdown",  // or "linear" or "github"
     "created_at": "...",
     "version": "1.0",
     "bootstrap": true
   }
   ```

2. **For Linear platform:**
   ```text
   # Check Linear MCP server is available
   /mcp list

   # Should show "linear-server" with tools like:
   - create_issue
   - list_issues
   - update_issue
   ```

   Verify Linear API token is configured in Linear MCP server settings.

3. **For GitHub platform:**
   ```text
   # Check GitHub MCP server is available
   /mcp list

   # Should show "github" with tools like:
   - create_issue
   - list_issues
   - update_issue
   ```

   Verify GitHub token is configured in GitHub MCP server settings.

4. **For Markdown platform:**
   ```bash
   # Verify project directory exists
   ls -la .respec-ai/projects/

   # If missing, create it:
   mkdir -p .respec-ai/projects/
   ```

5. **Check file permissions**
   ```bash
   ls -la .respec-ai/
   # All directories should be writable (755 or 775 permissions)

   # Fix if needed:
   chmod -R 755 .respec-ai/
   ```

6. **Re-run initialization if configuration is corrupted**
   ```bash
   respec-ai init --platform [platform]
   # Then restart Claude Code
   ```

---

### Refinement Loop Stuck

**Problem:** Quality scores not improving, workflow seems stuck

**Symptoms:**
- Critic agent returns same score repeatedly
- Workflow doesn't progress to next phase
- Error: "Maximum iterations reached"

**Solution:**

1. **Provide additional context**

   The system will automatically prompt for user input after detecting stagnation. When prompted:
   - Add specific requirements or constraints
   - Clarify ambiguous objectives
   - Provide examples or references

2. **Check quality thresholds in feedback**

   Critic agents provide specific feedback. Review the feedback for:
   - Missing requirements
   - Unclear specifications
   - Technical concerns or blockers

3. **Manual refinement**

   If automated refinement stagnates:
   - Review the current document (plan/spec/code)
   - Make manual edits to address critic feedback
   - Re-run the workflow command

4. **Adjust expectations**

   Quality thresholds:
   - 80-100: Excellent, ready to proceed
   - 60-79: Good, minor improvements needed
   - 40-59: Needs work, iterate more
   - 0-39: Significant issues, major revision needed

5. **System behavior:**
   - Auto-escalates after max iterations (typically 3-5)
   - Detects stagnation when scores don't improve
   - Requests user input when stuck

---

### Package Installation Fails

**Problem:** `uv add respec-ai` fails or errors

**Symptoms:**
- Package not found
- Version conflicts
- Network errors

**Solution:**

1. **For TestPyPI (development):**
   ```bash
   # Ensure you're using the correct index
   uv add --index https://test.pypi.org/simple/ respec-ai
   ```

2. **Check Python version compatibility**
   ```bash
   python --version  # Must be 3.13+
   ```

3. **Update uv to latest version**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv --version
   ```

4. **Check network connectivity**
   ```bash
   curl -I https://test.pypi.org/simple/respec-ai/
   # Should return HTTP 200
   ```

5. **Clear uv cache if needed**
   ```bash
   rm -rf ~/.cache/uv
   uv add respec-ai
   ```

6. **Alternative: Install from Git (fallback)**
   ```bash
   uv add git+https://github.com/mmcclatchy/respec-ai.git
   ```

---

### Homebrew Installation Issues

**Problem:** `brew install` fails or Homebrew tap not found

**Symptoms:**
- Error: "Error: No available formula with the name \"respec-ai\""
- Tap not showing in `brew tap` list
- Installation hangs or fails with dependency errors

**Solution:**

1. **Verify tap is added:**
   ```bash
   brew tap
   # Should show: mmcclatchy/respec-ai
   ```

2. **If tap is missing:**
   ```bash
   brew tap mmcclatchy/respec-ai
   brew update
   brew install respec-ai
   ```

3. **Check Homebrew is up to date:**
   ```bash
   brew update
   brew --version
   ```

4. **For dylib errors (can be safely ignored):**
   - Error about pydantic_core dylib paths is cosmetic
   - Software will work despite the warning
   - The error message will mention "Failed to fix install linkage"
   - This doesn't affect functionality - `respec-ai --version` will still work

5. **Reinstall if needed:**
   ```bash
   brew uninstall respec-ai
   brew update
   brew install mmcclatchy/respec-ai/respec-ai
   ```

6. **Verify installation:**
   ```bash
   respec-ai --version
   # Should show current version (e.g., 0.5.15)
   ```

---

### Python Version Errors

**Problem:** Python version compatibility issues

**Symptoms:**
- Error: "Python 3.13+ required"
- Syntax errors in RespecAI code
- Import errors for modern Python features

**Solution:**

1. **Check current Python version**
   ```bash
   python --version
   python3 --version
   python3.13 --version  # Try specific version
   ```

2. **Install Python 3.13+**

   **macOS (using Homebrew):**
   ```bash
   brew install python@3.13
   ```

   **Linux (using apt):**
   ```bash
   sudo apt update
   sudo apt install python3.13
   ```

   **Using pyenv:**
   ```bash
   pyenv install 3.13
   pyenv global 3.13
   ```

3. **Verify uv uses correct Python version**
   ```bash
   cd /path/to/respec-ai
   uv python list
   uv sync  # Re-sync with correct Python version
   ```

4. **Specify Python version if needed**

   If multiple Python versions exist, you can specify Python 3.13 when registering:
   ```bash
   claude mcp remove respec-ai  # Remove existing registration
   claude mcp add --transport stdio respec-ai -- uv run --python 3.13 --directory /absolute/path/to/respec-ai respec-server
   ```

## Best Practices

### Strategic Planning

**Do:**
- Use `/respec-plan` which will automatically guide you through conversational discovery
- Be specific about business objectives when answering questions
- Include constraints and limitations
- Provide context about users and use cases

**Don't:**
- Skip strategic planning for large features
- Mix technical details with business objectives
- Rush through refinement loops
- Call `/respec-plan-conversation` directly (it's used internally by `/respec-plan`)

### Roadmap Planning

**Do:**
- Use `/respec-roadmap` for projects that benefit from phased decomposition
- Let the roadmap agent choose the phasing strategy that fits your project:
  - **Feature-based** for most application development (complete capabilities)
  - **Technical-layer** for infrastructure or platform projects (foundational components)
  - **Incremental-complexity** when requirements are evolving (MVP → enhancements)
  - **Risk-based** for innovative projects (tackle unknowns first)
- Ensure each phase delivers something testable and meaningful
- Consider dependencies between phases
- Define clear milestones for each phase

**Don't:**
- Force a specific number of phases without considering project needs
- Create phases that are too granular (sub-tasks, not complete features)
- Create phases that are too large (multiple independent features bundled)
- Skip phase validation before implementation
- Ignore phase dependencies

### Technical Specifications

**Do:**
- Reference strategic plan
- Include architecture decisions
- Document technology choices
- Consider security and performance

**Don't:**
- Skip spec creation before implementation
- Mix specs with code
- Ignore critic feedback

### Implementation

**Do:**
- Follow build plan structure
- Review generated code carefully
- Run tests after implementation
- Address quality feedback

**Don't:**
- Skip build planning
- Ignore code review feedback
- Bypass quality gates

### Project Setup

**Do:**
- Run `respec-ai validate` after initial setup
- Use `respec-ai status` to verify configuration
- Check MCP registration before starting work

**Don't:**
- Skip validation after setup
- Ignore validation warnings
- Mix different RespecAI versions across projects

### Platform Selection

**Do:**
- Choose platform based on team workflow
- Verify MCP server availability before setup
- Test platform integration after setup

**Don't:**
- Switch platforms mid-project
- Use external platforms without MCP servers
- Ignore platform capabilities

## Advanced Usage

### Custom Quality Thresholds

Configure refinement loop thresholds:

```bash
# Set via environment variables (future feature)
export RESPEC_AI_PLAN_THRESHOLD=80
export RESPEC_AI_SPEC_THRESHOLD=85
export RESPEC_AI_BUILD_THRESHOLD=90
```

### Multi-Phase Projects

For complex projects:

1. Use `/respec-roadmap` for overall structure
2. Create separate strategic plans per phase
3. Generate specifications for each phase
4. Implement phases sequentially

### Collaborative Workflows

**With Linear:**
- Team members comment on Linear issues
- Assign issues to team members
- Track progress in cycles
- Use labels for organization

**With GitHub:**
- Team collaboration via issue comments
- Assign issues to team members
- Track in project boards
- Use milestones for releases

**With Markdown:**
- Share files via Git repository
- Review via pull requests
- Track changes with Git history
- Collaborate async

## Local Development Setup

### Overview

For developers who want to contribute to RespecAI or test changes locally before deploying.

This section covers:
- Setting up the local development environment
- Configuring Claude Code to use your local MCP server
- Rapid iteration workflows for MCP tools and templates
- Testing and code quality procedures

### Prerequisites

Before starting local development, ensure you have:

- **Git** - Repository cloned locally
- **Python 3.11+** - Check with `python --version`
- **uv** - Package and version manager ([Install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker/Docker Desktop** - Required for MCP server functionality
- **Claude Code CLI** - For testing MCP server integration

### Quick Setup (Recommended)

The fastest way to set up local development is using the install script:

```bash
# 1. Clone and set up the repository
git clone git@github.com:mmcclatchy/respec-ai.git
cd respec-ai
uv sync

# 2. Run the install script from your project directory
cd ~/path/to/your/project
~/path/to/respec-ai/scripts/install-respec-ai.sh -n <PROJECT_NAME> -p <PLATFORM>
```

**Example:**
```bash
# For markdown platform (no external dependencies)
cd ~/myproject
~/coding/projects/respec-ai/scripts/install-respec-ai.sh -n myproject -p markdown

# For linear platform
cd ~/myproject
~/coding/projects/respec-ai/scripts/install-respec-ai.sh -n myproject -p linear
```

**What the script does:**
- ✅ Configures Claude Code to use your local RespecAI repository
- ✅ Sets up MCP server with `uv run respec-server`
- ✅ Uses in-memory state manager (default - clean slate on restart)
- ✅ Generates workflow files in your project
- ✅ No Docker required for memory mode

**After running:**
1. Restart Claude Code to load the local MCP server
2. Verify with `/mcp list` - should show `respec-ai` with 32 tools
3. Start developing!

---

### Alternative: Manual Configuration

If you prefer to configure manually without using the install script:

#### Step 1: Clone Repository

```bash
# Clone the repository
git clone git@github.com:mmcclatchy/respec-ai.git
cd respec-ai

# Install dependencies
uv sync

# Verify installation
uv run respec-server --help
```

#### Step 2: Register MCP Server with Claude Code

Use the Claude Code CLI to register your local MCP server:

```bash
cd /absolute/path/to/respec-ai
claude mcp add -s user -t stdio respec-ai -- uv run respec-server
```

**Example:**
```bash
cd ~/coding/projects/respec-ai
claude mcp add -s user -t stdio respec-ai -- uv run respec-server
```

**Note:** The `--` separator is required to prevent command arguments from being parsed as options.

**Verify registration:**
```bash
claude mcp list
# Should show "respec-ai" in the list
```

**Important Configuration Notes:**
- `"command": "uv"` - Uses uv to run the local server
- `"args": ["run", "respec-server"]` - Runs the respec-server entry point
- `"cwd"` - **MUST be an absolute path** to your local respec-ai repository
  - Example: `/Users/yourname/coding/projects/respec-ai`
  - Do NOT use relative paths like `~/coding/projects/respec-ai`

**Alternative Configuration (using Python directly):**

If you prefer not to use `uv`, you can run with Python:

```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "python",
      "args": ["-m", "src.mcp"],
      "cwd": "/absolute/path/to/respec-ai"
    }
  }
}
```

#### Step 3: Restart Claude Code

```bash
# Exit Claude Code completely
# Then restart
claude
```

In Claude Code, verify the local server is loaded:

```text
/mcp list
```

**Expected output:**
```text
Available MCP Servers:
  respec-ai
    ├─ 32 tools available
    ├─ create_project_plan
    ├─ store_project_plan
    ├─ get_project_plan
    └─ [other tools...]
```

### Choosing a State Manager

RespecAI supports two state management modes for local development:

#### Memory Mode (Default - Recommended for Development)

**Use for:**
- ✅ Rapid iteration on workflow logic
- ✅ Testing changes without data pollution
- ✅ Clean slate on every restart
- ✅ Fast startup (no database setup)

**Configuration:**

This is the default mode used in the local development setup above. The state manager is already configured when you set up your local MCP server.

**How it works:**
- State stored in memory only
- Restarting Claude Code clears all state
- No database required
- Perfect for testing workflow changes

**Example Claude Code Configuration:**
```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "uv",
      "args": ["run", "respec-server"],
      "cwd": "/absolute/path/to/respec-ai",
      "env": {
        "STATE_MANAGER": "memory"
      }
    }
  }
}
```

#### Database Mode (Future - Persistent State)

⚠️ **Status:** Stubbed for future implementation

**Will be used for:**
- Data persistence across restarts
- Testing multi-session workflows
- Production-like behavior

**Future Configuration (when available):**

When database support is implemented, you'll be able to use Docker Compose for persistent state:

```bash
# Start database and MCP server
cd /path/to/respec-ai
docker compose -f docker-compose.dev.yml up -d

# Claude Code will connect to the containerized MCP server
```

**Future Claude Code Configuration:**
```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "docker",
      "args": ["compose", "-f", "/absolute/path/to/respec-ai/docker-compose.dev.yml", "exec", "-T", "mcp-server", "respec-server"],
      "cwd": "/absolute/path/to/respec-ai",
      "env": {
        "STATE_MANAGER": "database"
      }
    }
  }
}
```

**Future Implementation Details:**
- PostgreSQL database with raw SQL + Pydantic models
- Docker Compose setup with volume-mounted code for live reloading
- Data survives MCP server restarts
- Requires Docker Compose

**Note:** Database mode is currently stubbed. Attempting to use it will raise a clear `NotImplementedError` with instructions to use memory mode. Database support coming in a future release.

---

### Development Workflows

#### MCP Server Development

**Making changes to MCP tools:**

1. **Edit files** in `src/mcp/tools/`
   ```bash
   vim src/mcp/tools/project_plan_tools.py
   ```

2. **Write/update tests** in `tests/unit/mcp/`
   ```bash
   vim tests/unit/mcp/test_project_plan_tools.py
   ```

3. **Run tests**
   ```bash
   uv run pytest tests/unit/mcp/ -v
   ```

4. **Restart Claude Code** to load changes
   ```bash
   # Exit and restart
   claude
   ```

5. **Test interactively**
   ```text
   /mcp list
   # Call tools directly or through commands
   ```

**Key Points:**
- **No publishing required** - Changes are immediate after Claude Code restart
- **Fast iteration** - Edit, test, restart, verify
- **Full MCP tool access** - Test with real Claude Code integration

**Adding New MCP Tools:**

1. Create tool in `src/mcp/tools/new_tool.py`
2. Register in `src/mcp/server.py::register_all_tools()`
3. Write tests in `tests/unit/mcp/test_new_tool.py`
4. Run tests: `uv run pytest tests/unit/mcp/`
5. Restart Claude Code to load new tool

#### Template Refinement

**Quick iteration on agent/command templates:**

**Method 1: Script Testing (Fastest)**

Generate and view templates without side effects:

```bash
uv run python scripts/generate_templates.py
```

This shows formatted markdown for all document types to stdout. Use this for:
- Quick verification of template changes
- Checking tool configurations
- Validating YAML frontmatter

**Method 2: Test in Isolated Project**

Test full template generation in a real project context:

```bash
cd /tmp
respec-ai init --platform markdown --project-name test-templates
cat .claude/agents/plan-analyst.md
cat .claude/commands/respec-plan.md
```

This verifies:
- Templates generate correctly
- Platform-specific tools are included
- File structure is correct

**Method 3: Live Testing in Claude Code**

Test templates with actual workflow execution:

1. Modify template in `src/platform/templates/agents/` or `src/platform/templates/commands/`
2. Run `respec-ai init` in a test project
3. Restart Claude Code to load updated templates
4. Test with `/respec-plan` or other commands
5. Verify behavior matches expectations

**Typical Template Changes:**

**Updating Agent Instructions:**
```bash
# 1. Edit agent template
vim src/platform/templates/agents/plan_analyst.py

# 2. Test generation
uv run python scripts/generate_templates.py

# 3. Run unit tests
uv run pytest tests/unit/templates/ -v

# 4. Test in real project
cd /tmp/test-project
respec-ai init --platform markdown
cat .claude/agents/plan-analyst.md
```

**Updating Command Configuration:**
```bash
# 1. Edit command strategy
vim src/platform/command_strategies/plan_command.py

# 2. Test generation
uv run python scripts/generate_templates.py

# 3. Verify in test project
cd /tmp/test-project
respec-ai init --platform linear
cat .claude/commands/respec-plan.md
```

#### Running Tests

**All Tests:**
```bash
uv run pytest tests/
```

**By Test Level:**
```bash
# Unit tests only (fast, isolated)
uv run pytest tests/unit/ -v

# Integration tests (component interactions)
uv run pytest tests/integration/ -v

# E2E tests (full workflows)
uv run pytest tests/e2e/ -v
```

**Specific Test Files:**
```bash
# Test specific MCP tools
uv run pytest tests/unit/mcp/test_project_plan_tools.py -v

# Test template generation
uv run pytest tests/unit/templates/test_template_generator.py -v

# Test platform strategies
uv run pytest tests/integration/test_platform_strategies.py -v
```

**With Coverage:**
```bash
# Generate HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Test Markers:**
```bash
# Run tests with specific markers
uv run pytest -m "integration" tests/
uv run pytest -m "mcp_orchestration" tests/
```

#### Code Quality

**Pre-commit Hooks (Automatic):**

Installed hooks run automatically on `git commit`:
- ✅ Ruff linting with auto-fix
- ✅ Ruff formatting
- ✅ Type checking (mypy)
- ✅ Markdown validation
- ✅ Docstring enforcement
- ✅ Import location validation

**Install Pre-commit Hooks:**
```bash
pre-commit install
```

**Manual Quality Checks:**

```bash
# Lint and auto-fix
uv run ruff check . --fix

# Type checking
uv run mypy src/

# Markdown linting
markdownlint-cli2 '**/*.md'
```

**Before Committing:**
```bash
# Run all quality checks
uv run pytest tests/ -v
uv run ruff check .
uv run mypy src/
```

### Switching Between Local and Production

**Local Development Mode:**

Use your local repository for development:

```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "uv",
      "args": ["run", "respec-server"],
      "cwd": "/Users/yourname/coding/projects/respec-ai"
    }
  }
}
```

Benefits:
- ✅ Changes immediate after Claude Code restart
- ✅ No publishing required
- ✅ Fast iteration
- ✅ Full debugging capabilities

**Production Mode:**

Use the installed version from Homebrew or uv tool:

```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "respec-server"
    }
  }
}
```

Benefits:
- ✅ Uses stable released version
- ✅ No local repository required
- ✅ Consistent with production deployments

**Switching Between Modes:**

1. Edit `~/.claude/config.json`
2. Add or remove the `cwd` parameter
3. Restart Claude Code

### Project Structure

**Key Directories:**

```text
respec-ai/
├── src/
│   ├── cli/                    # CLI commands and interface
│   ├── mcp/                    # MCP server and tools
│   │   ├── server.py          # MCP server creation
│   │   ├── tools/             # 32 MCP tools across 7 modules
│   │   └── __main__.py        # Entry point for respec-server
│   └── platform/
│       ├── templates/          # Agent and command templates
│       │   ├── agents/        # 12 agent templates
│       │   └── commands/      # 5 command templates
│       ├── template_generator.py
│       ├── template_coordinator.py
│       └── command_strategies/
├── tests/
│   ├── unit/                  # Unit tests (fast, isolated)
│   ├── integration/           # Integration tests
│   ├── e2e/                   # End-to-end tests
│   └── conftest.py           # Global fixtures
├── scripts/
│   ├── generate_templates.py # Template testing script
│   └── build.sh              # Build and release script
└── pyproject.toml            # Project configuration
```

**Important Files:**

- `src/mcp/server.py` - MCP server creation and tool registration
- `src/mcp/tools/` - All MCP tool implementations
- `src/platform/templates/` - Agent and command templates
- `tests/conftest.py` - Test fixtures and configuration
- `.pre-commit-config.yaml` - Code quality hooks

### Troubleshooting Local Development

#### MCP Server Not Starting

**Symptoms:**
- RespecAI doesn't appear in `/mcp list`
- Error messages in Claude Code output
- Server fails to initialize

**Solutions:**

1. **Verify `cwd` path is absolute and correct:**
   ```bash
   # Check the path exists
   ls -la /absolute/path/to/respec-ai

   # Should show the respec-ai repository contents
   ```

2. **Check `uv` is in PATH:**
   ```bash
   which uv
   # Should show: /Users/yourname/.cargo/bin/uv or similar

   uv --version
   # Should show: uv X.Y.Z
   ```

3. **Look for errors in Claude Code output:**
   - Check Claude Code terminal for error messages
   - Look for Python import errors
   - Verify all dependencies are installed: `uv sync`

4. **Test server manually:**
   ```bash
   cd /path/to/respec-ai
   uv run respec-server
   # Should start without errors
   ```

#### Changes Not Appearing

**Symptoms:**
- Modified MCP tools don't reflect in Claude Code
- Updated templates don't show in generated files
- Code changes seem to be ignored

**Solutions:**

1. **Restart Claude Code completely:**
   ```bash
   # Must fully exit and restart, not just reload
   # Exit Claude Code
   claude
   ```

2. **Verify you edited the correct file:**
   ```bash
   # Check file modification time
   ls -la src/mcp/tools/your_tool.py

   # Verify file contents
   cat src/mcp/tools/your_tool.py | grep "your change"
   ```

3. **Check for syntax errors:**
   ```bash
   # Test server starts without errors
   uv run python -m src.mcp

   # Run tests to catch errors
   uv run pytest tests/unit/mcp/ -v
   ```

4. **Verify configuration points to correct repository:**
   ```bash
   cat ~/.claude/config.json | grep -A 5 respec-ai
   # Should show correct cwd path
   ```

#### Tools Not Showing

**Symptoms:**
- New tools don't appear in `/mcp list`
- Tool count is lower than expected
- Specific tools are missing

**Solutions:**

1. **Check tools are registered in `src/mcp/server.py`:**
   ```python
   # Verify your tool is registered in register_all_tools()
   def register_all_tools(server: Server) -> None:
       # ... other tools ...
       register_your_tool(server)  # Should be here
   ```

2. **Verify import statements:**
   ```python
   # Check imports at top of server.py
   from src.mcp.tools.your_tool import register_your_tool
   ```

3. **Check MCP server logs for errors:**
   - Look for import errors in Claude Code output
   - Check for registration errors
   - Verify tool function signatures match MCP requirements

4. **Test tool registration:**
   ```bash
   # Run server and check output
   uv run respec-server
   # Look for successful registration messages
   ```

#### Test Failures

**Symptoms:**
- Tests fail after making changes
- New tests don't pass
- Unexpected test errors

**Solutions:**

1. **Run specific test with verbose output:**
   ```bash
   uv run pytest tests/unit/mcp/test_your_tool.py -v -s
   # -v for verbose, -s to see print statements
   ```

2. **Check test fixtures:**
   ```bash
   # Verify fixtures in tests/conftest.py
   cat tests/conftest.py | grep "your_fixture"
   ```

3. **Run tests in isolation:**
   ```bash
   # Run single test method
   uv run pytest tests/unit/mcp/test_your_tool.py::test_specific_function -v
   ```

4. **Clear pytest cache:**
   ```bash
   rm -rf .pytest_cache
   find . -type d -name __pycache__ -exec rm -rf {} +
   uv run pytest tests/ -v
   ```

## Getting Help

### Documentation

- **Architecture:** See `docs/ARCHITECTURE.md` for system design
- **Analysis:** See `docs/ARCHITECTURE_ANALYSIS.md` for implementation details
- **Development:** See `docs/ARCHITECTURAL_REALIGNMENT.md` for technical implementation

### Common Questions

**Q: Can I use RespecAI without an external platform?**
A: Yes, use the Markdown platform for local file-based workflows.

**Q: Can I switch platforms after setup?**
A: Yes, but you'll need to delete configuration and re-run setup. Existing work won't automatically migrate.

**Q: Do I need all the generated agents?**
A: Yes, agents work together in refinement loops. Removing agents may break workflows.

**Q: Can I customize the templates?**
A: Templates are generated fresh each time. Customization requires modifying the RespecAI MCP server code.

**Q: How do I update RespecAI?**
A: Pull latest changes from repository and re-run installation script. Existing projects won't be affected.

## Next Steps

1. **Install RespecAI** using the installation script
2. **Restart Claude Code** to load workflow commands
3. **Start planning** with `/respec-plan`
4. **Breakdown the plan into specifications** with `/respec-roadmap`
5. **Design and Refine specifications** with `/respec-spec`
6. **Implement features** with `/respec-build`
