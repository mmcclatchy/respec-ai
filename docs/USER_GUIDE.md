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

## Getting Started

### Prerequisites

**Required for all users:**
- **Claude Code CLI** installed and configured
- **Git** for repository access

**For RespecAI MCP Server (required):**
- **uv** (Python version and package manager) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Python 3.13+**
- **Unix-like operating system** (Linux, macOS, or Windows Subsystem for Linux)

**For platform integrations (optional):**
- **Linear MCP Server** - If using Linear platform
- **GitHub MCP Server** - If using GitHub platform
- **Markdown platform** - No additional requirements (uses local files)

**For containerized deployments (optional):**
- **Docker** (Linux)
- **Docker Desktop** (macOS, Windows, Windows Subsystem for Linux)

### Installation Overview

RespecAI installation has two parts:

1. **RespecAI Package Installation** (one-time) - Install the respec-ai package from PyPI
2. **Project Initialization** (per-project) - Initialize RespecAI in your projects

Both parts can be completed with a single command.

### Part 1: RespecAI Package Installation (One-Time)

This installs the RespecAI package and makes the CLI available globally.

#### Step 1: Install RespecAI from PyPI

**For development/testing (TestPyPI):**
```bash
# Install from TestPyPI
uv add --index https://test.pypi.org/simple/ respec-ai

# Verify installation
respec-ai --version
```

**For production (PyPI):**
```bash
# Install from PyPI
uv add respec-ai

# Verify installation
respec-ai --version
```

**Expected output:**
```text
respec-ai 0.2.0
```

#### Step 2: Register MCP Server (Automatic or Manual)

The MCP server can be registered automatically during project initialization (recommended) or manually.

**Option A: Automatic Registration (Recommended)**

The MCP server will be automatically registered when you run `respec-ai init` in your first project.

**Option B: Manual Registration**

If you prefer to register the MCP server separately:
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
