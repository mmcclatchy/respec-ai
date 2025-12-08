# RespecAI User Guide

**TL;DR:** RespecAI is a meta MCP server that generates platform-specific workflow tools for AI-driven specification-based development. Creates custom Claude Code commands and agents tailored to your project management platform (Linear, GitHub, or Markdown files).

## Quick Start

**Get started in 3 commands:**

```bash
# 1. Install RespecAI
uv tool install respec-ai

# 2. Initialize in your project
cd /path/to/your/project
respec-ai init -p markdown

# 3. Restart Claude Code and start planning
claude
/respec-plan my-first-project
```

That's it! RespecAI will guide you through creating strategic plans, technical specs, and implementations.

---

## Table of Contents

- [Installation](#installation)
  - [Option A: uv Tool (Recommended)](#option-a-uv-tool-recommended---all-platforms)
  - [Option B: Homebrew (macOS and Linux)](#option-b-homebrew-macos-and-linux)
- [MCP Server Setup](#mcp-server-setup)
- [Project Initialization](#project-initialization)
- [Your First Workflow](#your-first-workflow)
- [CLI Reference](#cli-reference)
- [Available Workflows](#available-workflows)
- [Platform Selection](#platform-selection)
- [Configuration](#configuration)
- [Multi-Project Support](#multi-project-support)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Advanced Usage](#advanced-usage)
- [Local Development Setup](#local-development-setup)
- [Getting Help](#getting-help)

---

## Installation

### Prerequisites

**Required for all users:**
- **Claude Code CLI** installed and configured
- **Git** for repository access
- **Python 3.11+** for RespecAI
- **Docker or Docker Desktop** (required for MCP server functionality)

**For package installation:**
- **uv** (recommended) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **OR Homebrew** (macOS and Linux)

**For platform integrations (optional):**
- **Linear MCP Server** - If using Linear platform
- **GitHub MCP Server** - If using GitHub platform
- **Markdown platform** - No additional requirements (uses local files)

---

### Option A: uv Tool (Recommended - All Platforms)

**Best for:** Linux, macOS, Windows (WSL), or anyone preferring uv

**Installation:**

```bash
# Install RespecAI
uv tool install respec-ai

# Verify installation
respec-ai --version
```

**What gets installed:**
- ✅ respec-ai CLI tool in isolated environment
- ✅ All Python dependencies automatically
- ✅ Cross-platform compatibility
- ✅ Docker-based MCP server (registers automatically)

---

### Option B: Homebrew (macOS and Linux)

**Best for:** macOS or Linux users who prefer Homebrew

**Installation:**

```bash
# Add the RespecAI tap
brew tap mmcclatchy/respec-ai

# Install respec-ai
brew install respec-ai

# Verify installation
respec-ai --version
```

**What gets installed:**
- ✅ respec-ai CLI tool
- ✅ All Python dependencies (pydantic, rich, docker, etc.)
- ✅ Isolated virtualenv (no conflicts with system Python)
- ✅ Docker-based MCP server (registers automatically)

**Note:** You may see a harmless dylib linkage warning during installation - this can be safely ignored.

---

## MCP Server Setup

The MCP server is automatically registered during project initialization. You can also register it manually.

### Automatic Registration (Recommended)

The MCP server registers automatically when you run `respec-ai init` in your first project. Skip to [Project Initialization](#project-initialization).

### Manual Registration

If you prefer to register the MCP server separately:

```bash
# Register the MCP server
respec-ai register-mcp

# Or force re-registration if needed
respec-ai register-mcp --force
```

**Expected output:**
```text
RespecAI MCP server registered successfully
Package path: /path/to/installed/respec-ai
Restart Claude Code to activate the MCP server
```

**What this does:**
- ✅ Registers RespecAI MCP server with Claude Code
- ✅ Configures Docker-based server execution
- ✅ Automatically adds MCP tool permissions to Claude settings
- ✅ Creates necessary configuration in `~/.claude/config.json`

### Verify MCP Server

**Restart Claude Code** to load the MCP server:

```bash
claude
```

In Claude Code, verify the server is available:

```text
/mcp list
```

**Expected output:**
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

**If RespecAI doesn't appear**, see [Troubleshooting: MCP Server Not Available](#respecai-mcp-server-not-available).

---

## Project Initialization

Initialize RespecAI in any project directory.

### Initialize Your Project

**Step 1: Navigate to your project**

```bash
cd /path/to/your/project
```

**Step 2: Initialize RespecAI**

```bash
# Choose your platform: linear, github, or markdown
respec-ai init -p markdown

# Optional: specify project name (short flags)
respec-ai init -p linear -n my-project

# Optional: skip automatic MCP registration (long flag)
respec-ai init -p github --skip-mcp-registration

# Optional: force overwrite existing configuration (short flag)
respec-ai init -p markdown -f
```

**What this creates:**
- `.claude/commands/` - 5 RespecAI workflow commands
- `.claude/agents/` - 12 RespecAI workflow agents
- `.respec-ai/config.json` - Platform configuration

**Expected output:**
```text
✅ RespecAI setup complete!

Setting              Value
Platform             markdown
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

### Verify Project Setup

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
Platform             markdown
Config Version       0.6.3
Package Version      0.6.3
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

**If verification fails**, see [Troubleshooting](#troubleshooting).

---

## Your First Workflow

Now that setup is complete, try creating your first strategic plan:

```bash
# Start Claude Code in your project
cd /path/to/your/project
claude
```

**Example workflow:**

```text
# Start with strategic planning
/respec-plan my-first-project

# Claude will guide you through conversational discovery:
# - What problem are you solving?
# - Who are the users?
# - What are the key features?
# - What are the constraints?

# After planning, create a phased roadmap (for larger projects)
/respec-roadmap my-first-project

# Create detailed technical specifications
/respec-spec phase-1-auth

# Implement the specification
/respec-build phase-1-auth
```

Each command will guide you through the workflow with quality checks and refinement loops.

**See [Available Workflows](#available-workflows) for detailed documentation on each command.**

---

## CLI Reference

RespecAI provides comprehensive CLI commands for managing your workflow setup.

### Core Commands

#### `respec-ai init`

Initialize RespecAI in the current project.

**Usage:**
```bash
respec-ai init --platform <platform> [OPTIONS]
```

**Arguments:**
- `--platform` (required) - Platform type: `linear`, `github`, or `markdown`
- `--project-name` (optional) - Project name (defaults to directory name)
- `--skip-mcp-registration` (optional) - Skip automatic MCP server registration
- `--force` (optional) - Overwrite existing configuration

**Examples:**
```bash
# Initialize with Linear platform
respec-ai init -p linear

# Initialize with custom project name (short flags)
respec-ai init -p github -n my-app

# Initialize without MCP registration (long flags)
respec-ai init --platform markdown --skip-mcp-registration

# Force overwrite existing installation (short flag)
respec-ai init -p linear -f
```

---

#### `respec-ai rebuild`

Rebuild project configuration and templates (useful after RespecAI updates).

**Usage:**
```bash
respec-ai rebuild [OPTIONS]
```

**Options:**
- `--skip-mcp-registration` (optional) - Skip MCP server re-registration

**Example:**
```bash
# Rebuild configuration and re-register MCP server
respec-ai rebuild

# Rebuild without MCP re-registration
respec-ai rebuild --skip-mcp-registration
```

**Output:**
```text
Project rebuilt successfully
Platform: markdown
Project: my-project
Version: 0.6.3
Regenerated 5 commands and 12 agents

⚠ Restart Claude Code to activate the updated MCP server
```

**When to use:**
- After updating RespecAI package
- When templates are out of sync with package version
- To refresh MCP server registration

---

#### `respec-ai platform`

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

**Note:** Existing work (plans, specs) won't automatically migrate between platforms.

---

#### `respec-ai status`

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
Platform             markdown
Config Version       0.6.3
Package Version      0.6.3
MCP Server           RespecAI (✓ Registered)

Generated Files
Category            Count
Commands            5
Agents              12
```

---

#### `respec-ai validate`

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
Platform Valid       ✓ Platform: markdown
Version Current      ✓ Version: 0.6.3
Commands Directory   ✓ 5 commands found
Agents Directory     ✓ 12 agents found
MCP Registered       ✓ RespecAI server registered
```

---

#### `respec-ai regenerate`

Regenerate agent and command templates to match the current package version.

**Usage:**
```bash
respec-ai regenerate [--force]
```

**Options:**
- `--force` (optional) - Regenerate templates even if version is current

**Example:**
```bash
# Regenerate templates
respec-ai regenerate

# Force regeneration (short flag)
respec-ai regenerate -f
```

**Output:**
```text
Templates updated: 0.5.0 → 0.6.3
Regenerated 5 commands and 12 agents

⚠ Restart Claude Code to activate the updated templates
```

---

#### `respec-ai register-mcp`

Manually register the RespecAI MCP server in Claude Code.

**Usage:**
```bash
respec-ai register-mcp [--force] [--restore-backup]
```

**Options:**
- `--force` (optional) - Re-register even if already registered
- `--restore-backup` (optional) - Restore Claude config from backup

**Example:**
```bash
# Initial registration
respec-ai register-mcp

# Force re-registration (short flag)
respec-ai register-mcp -f

# Restore config from backup (long flag)
respec-ai register-mcp --restore-backup
```

**Output:**
```text
RespecAI MCP server registered successfully
Package path: /path/to/installed/respec-ai
Restart Claude Code to activate the MCP server
```

**What this does:**
- Registers MCP server using Claude CLI
- Adds MCP tool permissions to Claude settings
- Creates configuration in `~/.claude/config.json`

**When to use:**
- If automatic registration was skipped during `respec-ai init`
- If MCP server registration was corrupted
- If you need to update the registration after moving the package

---

### Docker Commands

Manage the RespecAI Docker container (MCP server runs in Docker).

#### `respec-ai docker status`

Show Docker container and image status.

**Usage:**
```bash
respec-ai docker status
```

**Output:**
```text
RespecAI MCP Server Status

Container Status
Name                 Running    Image                  Created
respec-ai-0.6.3      Yes        respec-ai:0.6.3       2025-01-15 10:30

Image Status
Repository           Tag        Created                Size
respec-ai            0.6.3      2025-01-15 10:25      450 MB
respec-ai            latest     2025-01-15 10:25      450 MB

Docker Daemon:       ✓ Running
Container Running:   ✓ Yes
```

---

#### `respec-ai docker start`

Start the MCP server container.

**Usage:**
```bash
respec-ai docker start
```

**Output:**
```text
✓ Started MCP server container: respec-ai-0.6.3
```

---

#### `respec-ai docker stop`

Stop the MCP server container.

**Usage:**
```bash
respec-ai docker stop [--timeout N]
```

**Options:**
- `--timeout N` (optional) - Shutdown timeout in seconds (default: 10)

**Example:**
```bash
# Graceful stop (default timeout: 10 seconds)
respec-ai docker stop

# Custom timeout
respec-ai docker stop --timeout 30
```

---

#### `respec-ai docker restart`

Restart the MCP server container.

**Usage:**
```bash
respec-ai docker restart
```

---

#### `respec-ai docker logs`

View MCP server container logs.

**Usage:**
```bash
respec-ai docker logs [-n N]
```

**Options:**
- `-n`, `--lines N` (optional) - Show last N lines (default: 100)

**Examples:**
```bash
# View last 100 lines (default)
respec-ai docker logs

# Show last 50 lines (short flag)
respec-ai docker logs -n 50

# Show last 200 lines (long flag)
respec-ai docker logs --lines 200
```

---

#### `respec-ai docker pull`

Pull the latest RespecAI Docker image.

**Usage:**
```bash
respec-ai docker pull
```

**Output:**
```text
✓ Pulled Docker image: respec-ai:0.6.3
```

---

#### `respec-ai docker build`

Build RespecAI Docker image locally (for development).

**Usage:**
```bash
respec-ai docker build [--no-cache]
```

**Options:**
- `--no-cache` (optional) - Build without using Docker cache

**Example:**
```bash
# Build with cache
respec-ai docker build

# Build without cache (clean build)
respec-ai docker build --no-cache
```

---

#### `respec-ai docker remove`

Remove the MCP server container.

**Usage:**
```bash
respec-ai docker remove [--force]
```

**Options:**
- `--force` (optional) - Remove even if container is running

**Example:**
```bash
# Remove stopped container
respec-ai docker remove

# Force remove running container (short flag)
respec-ai docker remove -f
```

---

#### `respec-ai docker cleanup`

Clean up old Docker resources.

**Usage:**
```bash
respec-ai docker cleanup [--dangling]
```

**Options:**
- `--dangling` (optional) - Remove dangling (untagged) images system-wide

**Examples:**
```bash
# Remove old RespecAI versions (keeps current version)
respec-ai docker cleanup

# Remove ALL dangling Docker images (WARNING: affects all Docker projects)
respec-ai docker cleanup -d
```

**Output (old versions):**
```text
✓ Cleaned up 2 old version(s)
```

**Output (dangling images):**
```text
WARNING: This will remove ALL dangling images system-wide
Dangling images are untagged images from failed builds/pulls
This affects all Docker projects, not just respec-ai

Continue? [y/N]: y

✓ Cleaned up 5 dangling images (reclaimed 1.2 GB)
```

**Note:** `--dangling` flag removes untagged images from ALL Docker projects, not just RespecAI. Use with caution.

---

### Utility Commands

#### `respec-ai mcp-server`

Start RespecAI MCP server directly (used internally by Claude Code).

**Usage:**
```bash
respec-ai mcp-server
```

**Note:** This command is primarily used by Claude Code's MCP server configuration. You typically won't run it manually.

**When to use:**
- Testing MCP server connection
- Debugging MCP server issues
- Verifying MCP server starts correctly

---

#### `respec-ai --version`

Show RespecAI package version.

**Usage:**
```bash
respec-ai --version
```

**Output:**
```text
respec-ai 0.6.3
```

---

#### `respec-ai --help`

Show help for CLI commands.

**Usage:**
```bash
# Show all commands
respec-ai --help

# Show help for specific command
respec-ai <command> --help
```

**Examples:**
```bash
# Show all commands
respec-ai --help

# Show init command help
respec-ai init --help

# Show docker command help
respec-ai docker --help
```

---

## Available Workflows

RespecAI provides four main workflow commands that work together to guide you from strategic planning to implementation.

### Understanding Commands and Agents

**Commands** (what you invoke with `/respec-*`) are the entry points to workflows. They orchestrate one or more agents to complete tasks.

**Agents** (invoked by commands) are specialized AI assistants with specific tools and responsibilities. You typically don't invoke agents directly.

---

### `/respec-plan`

**Purpose:** Create strategic project plans through interactive discovery

**Workflow:**
1. Uses conversational discovery to gather requirements
2. Creates strategic plan document
3. Evaluates plan quality with plan-critic agent
4. Refines through iterative improvement loops
5. Extracts business objectives with plan-analyst agent
6. Validates extraction with analyst-critic agent

**When to use:**
- Starting a new project or feature
- Need to understand business objectives
- Want structured strategic planning
- Requirements are unclear and need discovery

**Example:**
```text
User: /respec-plan my-auth-system

Claude: I'll help you create a strategic plan. Let me start by understanding your goals.

What problem are you trying to solve with this authentication system?

User: I need users to securely log in and access protected resources

Claude: Great! Let's explore this further. What types of users will use this system?
[Conversation continues with guided discovery...]

[After conversation]
Claude: Based on our discussion, I've created a strategic plan with these key objectives:
- Secure user authentication with JWT tokens
- Role-based access control
- Password reset functionality
- Session management

Quality Score: 85/100 (Excellent)

Would you like me to proceed with extracting business objectives?
```

---

### `/respec-plan-conversation`

**Purpose:** Interactive conversation for requirements gathering

**Workflow:**
1. Asks clarifying questions about project goals
2. Explores business objectives and constraints
3. Gathers context for strategic planning
4. Provides input for plan creation

**When to use:**
- **Do NOT invoke this directly** - it's used internally by `/respec-plan`
- Automatically run during `/respec-plan` workflow

**Note:** This is a sub-command that `/respec-plan` uses for conversational discovery.

---

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
- Clear strategic plan exists

**Example:**
```text
User: /respec-roadmap my-saas-platform

Claude: I'll create a multi-phase implementation roadmap based on your strategic plan.

[Analyzing project scope...]

I've created a 4-phase roadmap:

Phase 1: User Authentication & Authorization (2-3 weeks)
- JWT token-based authentication
- Role-based access control
- Password reset flow

Phase 2: Core Features (4-6 weeks)
- Dashboard and analytics
- User profile management
- Settings and preferences

Phase 3: Payment Integration (2-3 weeks)
- Stripe integration
- Subscription management
- Billing history

Phase 4: Advanced Features (3-4 weeks)
- Team collaboration
- Advanced reporting
- API access

Quality Score: 88/100 (Excellent)

I've also created initial specifications for each phase.
Would you like me to refine any phase?
```

---

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
- Want architecture and technology decisions documented

**Example:**
```text
User: /respec-spec phase-1-auth

Claude: I'll create a technical specification from your strategic plan.

[Retrieving plan: my-saas-platform...]
[Generating technical specification...]

Technical Specification: Phase 1 - User Authentication

Architecture:
- FastAPI backend with JWT token generation
- PostgreSQL for user storage
- bcrypt for password hashing
- Redis for session management

Implementation Approach:
1. User registration endpoint with validation
2. Login endpoint with JWT generation
3. Password reset flow with email tokens
4. Role-based middleware for route protection

Security Considerations:
- HTTPS only in production
- Rate limiting on auth endpoints
- Password complexity requirements
- Token expiration and refresh strategy

Quality Score: 92/100 (Excellent)

Creating Linear issue...
✓ Created: AUTH-123 "Phase 1: User Authentication"
```

---

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
- Need TDD-driven implementation

**Example:**
```text
User: /respec-build phase-1-auth

Claude: I'll implement the specification with automated code generation.

[Retrieving spec: AUTH-123...]
[Creating build plan...]

Build Plan Quality Score: 89/100 (Excellent)

Implementation Steps:
1. Create user model and database schema
2. Implement registration endpoint
3. Implement login endpoint with JWT
4. Create password reset flow
5. Add role-based middleware
6. Write comprehensive tests

[Generating code...]

✓ Created: src/models/user.py
✓ Created: src/api/auth.py
✓ Created: src/middleware/auth_middleware.py
✓ Created: tests/test_auth.py

Code Review Quality Score: 94/100 (Excellent)

All tests passing (24 tests)
Code coverage: 96%

Implementation complete!
```

---

## Quality & Refinement Loops

RespecAI uses two types of quality loops to ensure high-quality outputs:

### 1. Human-in-the-Loop with Quality Validation

**Used by:** `/respec-plan`

**Process:**
1. **Conversation:** Interactive Q&A to gather requirements
2. **Generation:** Creates strategic plan from conversation context
3. **Quality Check:** plan-critic evaluates and provides score
4. **Human Review:** User sees quality score and decides next action
5. **Analysis:** plan-analyst extracts structured business objectives
6. **Validation:** analyst-critic validates through automated refinement loop
7. **Completion:** Final validated strategic plan

**This is a hybrid approach** - conversational gathering with automated quality validation and user decision points.

### 2. Automated Refinement Loops (MCP-Driven)

**Used by:** `/respec-roadmap`, `/respec-spec`, `/respec-build`

**Process:**
1. **Generation:** Generative agent creates content (roadmap, spec, build plan, code)
2. **Evaluation:** Critic agent scores quality (0-100)
3. **Decision:** MCP server determines next action:
   - **High score** → Proceed to next phase
   - **Improving score** → Refine with feedback
   - **Stagnation** → Request user input

### Critic Agents

**For Human-in-the-Loop:**

**plan-critic:**
- Evaluates strategic plans after conversational gathering
- Provides quality score for user decision-making
- No automated refinement loop - user decides next action

**analyst-critic:**
- Validates business objective extraction
- Uses MCP-driven automated refinement loop
- Ensures completeness and accuracy of analysis

**For Automated Loops:**

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

---

## Configuration

### Platform Configuration

Platform selection stored in `.respec-ai/config.json`:

```json
{
  "platform": "markdown",
  "project_name": "my-project",
  "created_at": "2025-01-15T12:00:00.000000",
  "version": "0.6.3"
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
# Update the package (uv tool)
uv tool upgrade respec-ai

# OR update via Homebrew
brew upgrade respec-ai

# Rebuild your project templates
cd /path/to/your/project
respec-ai rebuild
```

This preserves your platform choice while updating templates to the latest version.

---

## Multi-Project Support

**Status**: ✅ Fully Supported

### Current Implementation

RespecAI supports running multiple projects with explicit project context. Each project maintains its own:

- ✅ Platform configuration (`.respec-ai/config.json`)
- ✅ Command templates (`.claude/commands/*.md`)
- ✅ Agent templates (`.claude/agents/*.md`)
- ✅ Explicit project context via `project_path` parameter
- ✅ Linear/GitHub issues (naturally isolated by workspace/repository)

**What This Means:**
- All 29+ MCP tools accept explicit `project_path` parameter
- Multiple projects can use the same RespecAI MCP server
- Each project's workflows operate independently when project_path is specified
- No cross-project interference at the tool level

### Current Architecture

**What Works Now:**
- ✅ Tool-level multi-project support (explicit `project_path`)
- ✅ Different projects can use different platforms
- ✅ Simultaneous project usage (with proper project_path specification)
- ✅ All 391+ tests passing with multi-project scenarios

**Current Limitations:**
- ⏸️ **In-memory state**: Plans, specs, and loop state stored in memory
  - State does not persist across MCP server restarts
  - Acceptable for single-user development workflows
- ⏸️ **Global configuration**: Platform config stored at project level

### Recommended Usage

**For single user / solo development**: Works perfectly with no limitations.

**For multiple projects**:
- ✅ Set up each project independently with `respec-ai init`
- ✅ Different projects can use different platforms
- ✅ Commands work correctly when project context is clear
- ⏸️ State resets on MCP server restart (acceptable for current use)

### Future Enhancements

**Database Persistence** (planned):
- Persistent state storage across server restarts
- Database-backed state management
- Enhanced multi-user support

---

## Troubleshooting

### RespecAI MCP Server Not Available

**Problem:** RespecAI doesn't appear in `/mcp list` output

**Solution:**

1. **Verify RespecAI package is installed**
   ```bash
   respec-ai --version
   ```

   Should show: `respec-ai 0.6.3` (or current version)

   If command not found:
   ```bash
   # For uv tool
   uv tool install respec-ai

   # For Homebrew
   brew install respec-ai
   ```

2. **Verify Docker is running**
   ```bash
   respec-ai docker status
   ```

   If Docker daemon is not running:
   - Start Docker Desktop (macOS/Windows)
   - Start Docker service (Linux): `sudo systemctl start docker`

3. **Register MCP server**
   ```bash
   respec-ai register-mcp
   ```

4. **Verify registration**
   ```bash
   cat ~/.claude/config.json | grep -A 10 RespecAI
   ```

   Should show RespecAI server configuration.

5. **Restart Claude Code**
   ```bash
   claude
   /mcp list
   ```

**If still not working:**
- Re-register with force: `respec-ai register-mcp --force`
- Check Docker logs: `respec-ai docker logs`
- Restart Docker container: `respec-ai docker restart`
- Check Python version: `python --version` (must be 3.11+)

---

### Docker Container Not Running

**Problem:** MCP server container is stopped or failing to start

**Symptoms:**
- `respec-ai docker status` shows container not running
- `/mcp list` doesn't show RespecAI
- Error messages about Docker connectivity

**Solution:**

1. **Check Docker daemon status**
   ```bash
   docker ps
   ```

   If error about Docker daemon not running:
   - Start Docker Desktop
   - Or `sudo systemctl start docker` (Linux)

2. **Start the container**
   ```bash
   respec-ai docker start
   ```

3. **Check container logs for errors**
   ```bash
   respec-ai docker logs
   ```

4. **If container fails to start, rebuild**
   ```bash
   # Pull latest image
   respec-ai docker pull

   # Or build locally
   respec-ai docker build
   ```

5. **Verify container is running**
   ```bash
   respec-ai docker status
   ```

**If still failing:**
- Check available disk space: `df -h`
- Check Docker logs: `docker logs respec-ai-0.6.3`
- Remove and recreate: `respec-ai docker remove && respec-ai docker start`

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
   respec-ai init --platform [your-platform] --force
   # Then restart Claude Code
   ```

4. **Verify RespecAI MCP server is available**
   ```text
   /mcp list  # Should show "RespecAI"
   ```

   If RespecAI MCP server is missing, see [RespecAI MCP Server Not Available](#respecai-mcp-server-not-available).

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
   cat .respec-ai/config.json
   ```

   Should show correct platform:
   ```json
   {
     "platform": "markdown",  // or "linear" or "github"
     "created_at": "...",
     "version": "0.6.3"
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

---

### MCP Permissions Not Set

**Problem:** RespecAI tools require permission approval every time

**Symptoms:**
- Claude Code asks for permission to use RespecAI tools repeatedly
- Tools work but require manual approval each time

**Solution:**

The MCP permissions should be automatically set during `respec-ai init` or `respec-ai register-mcp`. If they weren't:

1. **Run register-mcp again**
   ```bash
   respec-ai register-mcp --force
   ```

   This will add the permissions automatically.

2. **Verify permissions were added**
   ```bash
   cat ~/.claude/settings.json | grep -A 5 permissions
   # OR
   cat ~/.claude/settings.local.json | grep -A 5 permissions
   ```

   Should show:
   ```json
   {
     "permissions": {
       "allow": [
         "mcp__respecai__*"
       ]
     }
   }
   ```

3. **Manually add if needed**

   Edit `~/.claude/settings.local.json` (or `~/.claude/settings.json`):
   ```json
   {
     "permissions": {
       "allow": [
         "mcp__respecai__*"
       ]
     }
   }
   ```

4. **Restart Claude Code**
   ```bash
   claude
   ```

---

### Package Installation Fails

**Problem:** Installation fails or errors

**Symptoms:**
- Package not found
- Version conflicts
- Network errors

**Solution:**

1. **For uv tool installation:**
   ```bash
   # Ensure uv is up to date
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv --version

   # Install RespecAI
   uv tool install respec-ai
   ```

2. **Check Python version compatibility**
   ```bash
   python --version  # Must be 3.11+
   ```

3. **Check network connectivity**
   ```bash
   curl -I https://pypi.org/simple/respec-ai/
   # Should return HTTP 200
   ```

4. **Clear uv cache if needed**
   ```bash
   uv cache clean
   uv tool install respec-ai
   ```

5. **For Homebrew installation:**
   ```bash
   # Update Homebrew
   brew update

   # Ensure tap is added
   brew tap mmcclatchy/respec-ai

   # Install
   brew install respec-ai
   ```

---

## Best Practices

### Strategic Planning

**Do:**
- Use `/respec-plan` for conversational discovery
- Be specific about business objectives when answering questions
- Include constraints and limitations
- Provide context about users and use cases

**Don't:**
- Skip strategic planning for large features
- Mix technical details with business objectives
- Rush through refinement loops
- Call `/respec-plan-conversation` directly (it's used internally)

### Roadmap Planning

**Do:**
- Use `/respec-roadmap` for projects that benefit from phased decomposition
- Let the roadmap agent choose the phasing strategy that fits your project
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

---

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

---

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
- ✅ Sets up MCP server with `uv run python -m src.mcp`
- ✅ Uses in-memory state manager (default - clean slate on restart)
- ✅ Generates workflow files in your project
- ✅ Adds MCP permissions to Claude settings
- ✅ No Docker required for memory mode

**After running:**
1. Restart Claude Code to load the local MCP server
2. Verify with `/mcp list` - should show `respec-ai` with 29+ tools
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
uv run python -m src.mcp --help
```

#### Step 2: Register MCP Server with Claude Code

Use the Claude Code CLI to register your local MCP server:

```bash
# Register using Python module syntax
claude mcp add -s user -t stdio respec-ai -- uv --directory /absolute/path/to/respec-ai run python -m src.mcp
```

**Example:**
```bash
claude mcp add -s user -t stdio respec-ai -- uv --directory ~/coding/projects/respec-ai run python -m src.mcp
```

**Important:**
- Uses `python -m src.mcp` to run the MCP server as a Python module
- `--directory` flag must point to absolute path (NOT relative path like `~`)
- Example absolute path: `/Users/yourname/coding/projects/respec-ai`

**Verify registration:**
```bash
claude mcp list
# Should show "respec-ai" in the list
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
    ├─ 29+ tools available
    ├─ create_project_plan
    ├─ store_project_plan
    ├─ get_project_plan
    └─ [other tools...]
```

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

#### Template Refinement

**Quick iteration on agent/command templates:**

**Method 1: Script Testing (Fastest)**

Generate and view templates without side effects:

```bash
uv run python scripts/generate_templates.py
```

**Method 2: Test in Isolated Project**

Test full template generation:

```bash
cd /tmp
respec-ai init --platform markdown --project-name test-templates
cat .claude/agents/plan-analyst.md
cat .claude/commands/respec-plan.md
```

**Method 3: Live Testing in Claude Code**

Test templates with actual workflow execution:

1. Modify template in `src/platform/templates/`
2. Run `respec-ai init` in test project
3. Restart Claude Code to load updated templates
4. Test with `/respec-plan` or other commands
5. Verify behavior matches expectations

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

**With Coverage:**
```bash
# Generate HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

#### Code Quality

**Pre-commit Hooks (Automatic):**

```bash
# Install pre-commit hooks
pre-commit install
```

Installed hooks run automatically on `git commit`:
- ✅ Ruff linting with auto-fix
- ✅ Ruff formatting
- ✅ Type checking (mypy)
- ✅ Markdown validation

**Manual Quality Checks:**

```bash
# Lint and auto-fix
uv run ruff check . --fix

# Type checking
uv run mypy src/

# Markdown linting
markdownlint-cli2 '**/*.md'
```

---

### Switching Between Local and Production

**Local Development Mode:**

```json
{
  "mcpServers": {
    "respec-ai": {
      "command": "uv",
      "args": ["--directory", "/Users/yourname/coding/projects/respec-ai", "run", "python", "-m", "src.mcp"]
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

```bash
# Switch to production package
claude mcp remove respec-ai
respec-ai register-mcp
```

This registers the installed package version instead of local development version.

---

### Troubleshooting Local Development

#### MCP Server Not Starting

**Solutions:**

1. **Verify path is absolute and correct:**
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

3. **Test server manually:**
   ```bash
   cd /path/to/respec-ai
   uv run python -m src.mcp
   # Should start without errors
   ```

#### Changes Not Appearing

**Solutions:**

1. **Restart Claude Code completely:**
   ```bash
   # Must fully exit and restart
   claude
   ```

2. **Verify you edited the correct file:**
   ```bash
   # Check file modification time
   ls -la src/mcp/tools/your_tool.py
   ```

3. **Check for syntax errors:**
   ```bash
   # Test server starts
   uv run python -m src.mcp

   # Run tests
   uv run pytest tests/unit/mcp/ -v
   ```

---

## Getting Help

### Documentation

- **User Guide:** This document
- **Architecture:** See `docs/ARCHITECTURE.md` for system design
- **Multi-Project Design:** See `docs/MULTI_PROJECT_DESIGN.md`

### Common Questions

**Q: Can I use RespecAI without an external platform?**
A: Yes, use the Markdown platform for local file-based workflows.

**Q: Can I switch platforms after setup?**
A: Yes, use `respec-ai platform <new-platform>`. Existing work won't migrate automatically.

**Q: Do I need all the generated agents?**
A: Yes, agents work together in refinement loops. Removing agents may break workflows.

**Q: Can I customize the templates?**
A: Templates are regenerated on init/rebuild. Customization requires modifying source code.

**Q: How do I update RespecAI?**
A: Run `uv tool upgrade respec-ai` or `brew upgrade respec-ai`, then `respec-ai rebuild` in your projects.

**Q: Does the MCP server require Docker?**
A: Yes, the production MCP server runs in Docker. For local development, you can run directly with `uv run python -m src.mcp`.

---

## What is RespecAI?

RespecAI is a **meta MCP server** that generates platform-specific workflow tools for AI-driven specification-based development.

### Key Benefits

- **Platform flexibility** - Work with Linear issues, GitHub issues, or local Markdown files
- **Automated setup** - Generate complete workflow tools with a single command
- **Type-safe integration** - Platform-specific tools properly configured for your environment
- **Refinement loops** - Quality-driven development with critic agents and iterative improvement
- **Docker-based MCP server** - Isolated, containerized execution for reliability

### Current Status

**Production Ready** - RespecAI is stable for real-world usage:
- ✅ MCP server fully functional
- ✅ Multi-project architecture implemented
- ✅ All 29+ tools operational
- ✅ 391+ tests passing
- ✅ Installation and setup validated
- ✅ Docker-based deployment
