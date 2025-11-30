# Specter User Guide

Complete guide to using Specter for AI-driven specification-based development.

## What is Specter?

Specter is a **meta MCP server** that generates platform-specific workflow tools for AI-driven development. It creates custom Claude Code commands and agents tailored to your project management platform (Linear, GitHub, or local Markdown files).

### Key Benefits

- **Platform flexibility** - Work with Linear issues, GitHub issues, or local Markdown files
- **Automated setup** - Generate complete workflow tools with a single command
- **Type-safe integration** - Platform-specific tools properly configured for your environment
- **Refinement loops** - Quality-driven development with critic agents and iterative improvement

### Current Status

**MVP Complete** - Specter is ready for real-world usage:
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

**For Specter MCP Server (required):**
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

Specter installation has two parts:

1. **Specter MCP Server Setup** (one-time) - Configure Specter as an MCP server in Claude Code
2. **Project Setup** (per-project) - Generate workflow files for each project

### Part 1: Specter MCP Server Setup (One-Time)

This configures Specter as an MCP server that Claude Code can use across all your projects.

#### Step 1: Clone Specter Repository

```bash
# Choose a location for the Specter repository
# Recommended: alongside your other projects
cd ~/coding/projects  # or your preferred location

# Clone the repository
git clone git@github.com:mmcclatchy/specter.git
cd specter
```

> **Note**: For private repositories, ensure your SSH key is configured with GitHub.

#### Step 2: Install Dependencies

```bash
# Install Python dependencies using uv
uv sync
```

**Expected output:**
```text
Resolved XX packages in XXms
Installed XX packages in XXms
```

**If you see errors:**
- Verify Python 3.13+ is installed: `python --version` or `python3 --version`
- Install uv if missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`

#### Step 3: Register Specter MCP Server with Claude Code

Add Specter to your Claude Code MCP configuration using the `claude mcp add` command.

**Run this command** (replace the path with your actual Specter location from Step 1):

```bash
claude mcp add --transport stdio specter -- uv run --directory /absolute/path/to/specter specter-server
```

**Example with actual path:**
```bash
# If you cloned to ~/coding/projects/specter:
claude mcp add --transport stdio specter -- uv run --directory /Users/username/coding/projects/specter specter-server
```

**Important notes:**
- Replace `/absolute/path/to/specter` with your actual Specter directory
- Use **absolute paths** not relative paths or `~`
  - ✅ Correct: `/Users/username/coding/projects/specter`
  - ❌ Wrong: `~/coding/projects/specter` (tilde won't expand)
  - ❌ Wrong: `../specter` (relative paths won't work)
- The `--directory` flag tells `uv` where to find the Specter project

**Expected output:**
```text
✓ Successfully added MCP server: specter
```

#### Step 4: Verify MCP Server

**Restart Claude Code** to load the new configuration, then verify:

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
  specter
    ├─ 29+ tools available
    ├─ create_project_plan
    ├─ store_project_plan
    ├─ initialize_refinement_loop
    └─ [other tools...]
```

**✓ Success criteria:**
- Specter appears in the MCP server list
- Tool count shows 29+ tools
- No error messages

**If Specter doesn't appear**, see [Troubleshooting](#platform-mcp-server-not-found) below.

---

### Part 2: Project Setup (Per-Project)

Now that Specter MCP Server is configured, you can set up any project to use Specter workflows.

#### Installation Method Selection

Choose the installation method based on your needs:

| Method | Best For | Repository Access | Steps |
|--------|----------|-------------------|-------|
| **Local Script** | Development, private repos | Local clone required | 3 |
| **Remote Curl** | Public repos, quick setup | Public URL only | 2 |
| **Bootstrap** | When script fails, manual setup | MCP server required | 3 |

#### Method 1: Local Script Installation (Recommended for Private Repos)

Use this method when you have Specter cloned locally (from Part 1).

**Step 1: Navigate to your project**
```bash
cd /path/to/your/project
```

**Step 2: Run installation script**
```bash
# Navigate to your project directory first
cd ~/path/to/your/project

# Run installation script with platform choice
~/coding/projects/specter/scripts/install-specter.sh --platform linear
# or --platform github
# or --platform markdown
```

This creates:
- `.claude/commands/` - All Specter workflow commands
- `.claude/agents/` - All Specter workflow agents
- `.specter/config.json` - Platform configuration

**Expected output:**
```text
✅ Specter setup complete!

Platform: linear
Files Created: 15
Location: /path/to/your/project

⚠️  IMPORTANT: Restart Claude Code to activate the new commands!

Available Commands (after restart):
  • /specter-plan - Create strategic plans
  • /specter-spec - Transform plans into technical specifications
  • /specter-build - Execute implementation workflows
  • /specter-roadmap - Create phased roadmaps
  • /specter-plan-conversation - Convert conversations into plans

🚀 Ready to begin! Restart Claude Code to use the Specter commands.
```

**Step 3: Restart Claude Code**
```bash
# Exit and restart Claude Code to load new commands
claude
```

---

#### Method 2: Remote Curl Installation (Public Repos Only)

> **⚠️ Important**: This method only works for **public repositories**. For private repos, use Method 1 or Method 3.

**Step 1: Run remote installation**
```bash
cd /path/to/your/project

# Choose your platform: linear, github, or markdown
curl -fsSL https://raw.githubusercontent.com/mmcclatchy/specter/main/scripts/install-specter.sh | bash -s -- --platform linear
```

This installs all workflow files and creates platform configuration.

**Step 2: Restart Claude Code**
```bash
# Exit and restart Claude Code to load new commands
claude
```

---

### Verify Project Setup

After completing any installation method, verify your project setup:

```bash
# Check directory structure
ls -la .claude/commands/specter-*.md
ls -la .claude/agents/*.md
ls -la .specter/config/platform.json

# Check platform configuration
cat .specter/config/platform.json
```

**Expected structure:**
```text
project/
├── .claude/
│   ├── commands/
│   │   ├── specter-plan.md
│   │   ├── specter-roadmap.md
│   │   ├── specter-spec.md
│   │   ├── specter-build.md
│   │   └── specter-plan-conversation.md
│   └── agents/
│       ├── plan-analyst.md
│       ├── plan-critic.md
│       ├── analyst-critic.md
│       ├── roadmap.md
│       ├── roadmap-critic.md
│       └── create-spec.md
└── .specter/
    ├── config/
    │   └── platform.json
    └── projects/ (created when using markdown platform)
```

**Verification checklist:**
- [ ] All 5 commands exist in `.claude/commands/`
- [ ] Agent files exist in `.claude/agents/`
- [ ] Platform configuration exists and shows correct platform
- [ ] Commands autocomplete with `/specter-` in Claude Code
- [ ] Specter MCP server shows in `/mcp list`

**If verification fails**, see [Troubleshooting](#commands-not-found) below.

---

### Quick Start: Your First Specter Workflow

Now that setup is complete, try creating your first plan:

```bash
# In your project directory
claude
```

```text
# Start with strategic planning
/specter-plan

# Or if you want to create a multi-phase roadmap
/specter-roadmap my-project-name
```

Follow the interactive prompts to create your first strategic plan. See [Available Commands](#available-commands) below for detailed workflow documentation.

---

## Multi-Project Support

**Status**: ✅ MVP Complete (Phase 1)

### Current Implementation

Specter supports running multiple projects with explicit project context. Each project maintains its own:

- ✅ Platform configuration (`.specter/config/platform.json`)
- ✅ Command templates (`.claude/commands/*.md`)
- ✅ Agent templates (`.claude/agents/*.md`)
- ✅ Explicit project context via `project_path` parameter
- ✅ Linear/GitHub issues (naturally isolated by workspace/repository)

**What This Means:**
- All 36+ MCP tools now accept explicit `project_path` parameter
- Multiple projects can use the same Specter MCP server
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
- ⏸️ **Global configuration**: Platform config stored at `~/.specter/projects/`
  - Works fine for solo development
  - Per-project config deferred until team collaboration features needed

### Recommended Usage (MVP)

**For single user / solo development**: Works perfectly with no limitations.

**For multiple projects**:
- ✅ Set up each project independently with `/init-specter`
- ✅ Different projects can use different platforms
- ✅ Commands work correctly when project context is clear
- ⏸️ State resets on MCP server restart (acceptable for MVP)

### Future Enhancements (Post-MVP)

**Database Persistence** (planned, not file-based):
- Persistent state storage across server restarts
- Database-backed state management
- Enhanced multi-user support

**Per-Project Configuration** (when team collaboration needed):
- Move config from `~/.specter/projects/` to `.specter/config/`
- Repository-portable configuration
- Better team workflow support

**See [MULTI_PROJECT_DESIGN.md](MULTI_PROJECT_DESIGN.md) and [SETUP_IMPROVEMENTS.md](SETUP_IMPROVEMENTS.md) for:**
- Complete architecture details
- Phase 1 implementation (completed)
- Future enhancement roadmap
- Technical implementation notes

---

## Platform Selection

### Choosing Your Platform

Specter supports three platforms with different capabilities:

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
- Specs stored as markdown files in `.specter/projects/[project-name]/specter-specs/`
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

**Commands** (what you invoke with `/specter-*`) use `allowed-tools:` in their frontmatter:
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

### `/specter-plan`

**Purpose:** Create strategic project plans through interactive discovery

**Workflow:**
1. Uses `/specter-plan-conversation` for natural language requirements gathering
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
User: /specter-plan

Claude: I'll help you create a strategic plan. Let me start by understanding your goals.

[Interactive conversation begins...]
```

### `/specter-plan-conversation`

**Purpose:** Interactive conversation for requirements gathering

**Workflow:**
1. Asks clarifying questions about project goals
2. Explores business objectives and constraints
3. Gathers context for strategic planning
4. Provides input for plan creation

**When to use:**
- This is not to be used by end-users
- This command is used as a subcommand of `/specter-plan`

### `/specter-roadmap`

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
User: /specter-roadmap [project-name]

Claude: I'll create a multi-phase implementation roadmap.
[Generates roadmap with phases, milestones, and initial specs]
```

### `/specter-spec`

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
User: /specter-spec [spec-name]

Claude: I'll create a technical specification from your strategic plan.
[Generates spec with technical details, architecture, and implementation approach]
```

### `/specter-build`

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
User: /specter-build [spec-name]

Claude: I'll implement the specification with automated code generation.
[Creates build plan, generates code, reviews quality]
```

## Workflow Examples

### Example 1: New Feature Development

**Scenario:** Adding user authentication to an application

```text
1. Strategic Planning:
   User: /specter-plan [project-name]
   [Interactive conversation about authentication needs]
   → Creates strategic plan with business objectives

2. Technical Specification:
   User: /specter-spec [spec-name]
   → Generates technical spec with architecture details
   → Creates Linear issue (or GitHub issue, or markdown file)

3. Implementation:
   User: /specter-build [spec-name]
   → Creates build plan with implementation steps
   → Generates authentication code
   → Reviews code quality
   → Implements feature
```

### Example 2: Large Project Roadmap

**Scenario:** Building a complete SaaS application

```text
1. Strategic Planning:
   User: /specter-plan [project-name]
   → Creates strategic plan for entire SaaS application
   → Defines business objectives and high-level requirements

2. Roadmap Creation:
   User: /specter-roadmap [project-name]
   → Breaks down strategic plan into implementation phases:
     - Phase 1: User authentication
     - Phase 2: Core features
     - Phase 3: Payment integration
     - Phase 4: Analytics dashboard
   → Creates initial specs for each phase automatically

3. Phase Implementation:
   For each phase/spec created by roadmap:
   User: /specter-spec [spec-name] (to elaborate technical details)
   User: /specter-build [spec-name] (to implement the phase)
```

### Example 3: Requirements Discovery

**Scenario:** Unclear project requirements

```text
1. Strategic Planning with Conversational Discovery:
   User: /specter-plan [project-name]
   Claude: (runs /specter-plan-conversation internally)
   Claude: What problem are you trying to solve?
   User: I want users to collaborate in real-time
   Claude: What kind of collaboration? Document editing? Chat? Screen sharing?
   [Conversation continues to clarify requirements]
   → Claude creates strategic plan based on conversation
   → Evaluates and refines plan through quality loops

2. Continue with roadmap or spec creation...
```

## Quality & Refinement Loops

Specter uses two types of quality loops:

### 1. Human-in-the-Loop with Quality Validation

**Used by:** `/specter-plan`

**Process:**
1. **Conversation:** `/specter-plan-conversation` conducts interactive Q&A to gather requirements
2. **Generation:** Creates strategic plan from conversation context
3. **Quality Check:** `plan-critic` evaluates the plan and provides quality score
4. **Human Review:** User sees quality score and decides: continue conversation, refine plan, or accept
5. **Analysis:** `plan-analyst` extracts structured business objectives
6. **Validation:** `analyst-critic` validates the extraction through MCP refinement loop
7. **Completion:** Final validated strategic plan

This is a **hybrid approach** - conversational gathering with automated quality validation and user decision points.

### 2. Automated Refinement Loops (MCP-Driven)

**Used by:** `/specter-roadmap`, `/specter-spec`, `/specter-build`

**Process:**
1. **Generation:** A generative agent creates content (roadmap, spec, build plan, code)
2. **Evaluation:** A critic agent scores quality (0-100)
3. **Decision:** MCP server determines next action:
   - **High score** → Proceed to next phase
   - **Improving score** → Refine with feedback
   - **Stagnation** → Request user input

### Critic Agents

**For Human-in-the-Loop (`/specter-plan`):**

**plan-critic:**
- Evaluates strategic plans after conversational gathering
- Provides quality score for user decision-making
- No automated refinement loop - user decides next action

**analyst-critic:**
- Validates business objective extraction
- Uses MCP-driven automated refinement loop
- Ensures completeness and accuracy of analysis

**For Automated Loops (`/specter-roadmap`, `/specter-spec`, `/specter-build`):**

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
1. /specter-plan creates strategic plan
2. Stored as Linear project
3. Issues linked to project
4. Cycles used for sprint planning
```

**Spec Creation:**
```text
1. /specter-spec creates Linear issue
2. Issue contains technical specification
3. Comments added for feedback
4. Labels applied for categorization
5. Project assigned for tracking
```

### GitHub Workflow

**Plan Storage:**
```text
1. /specter-plan creates strategic plan
2. Stored as GitHub project board
3. Issues linked to project
4. Milestones for phases
```

**Spec Creation:**
```text
1. /specter-spec creates GitHub issue
2. Issue contains technical specification
3. Comments for feedback
4. Labels for categorization
5. Milestone for tracking
```

### Markdown Workflow

**Plan Storage:**
```text
1. /specter-plan creates markdown file
2. Stored in .specter/projects/[project-name]/project_plan.md
3. Structured sections
4. Git commit for history
```

**Spec Creation:**
```text
1. /specter-spec creates markdown file
2. Stored in .specter/projects/[project-name]/specter-specs/
3. Structured markdown format
4. Git-friendly version control
5. Comments as markdown sections
```

## Configuration

### Platform Configuration

Platform selection stored in `.specter/config/platform.json`:

```json
{
  "platform": "linear",
  "created_at": "2025-10-01T12:00:00.000000",
  "version": "1.0",
  "bootstrap": true
}
```

### Changing Platforms

To switch platforms, simply re-run the installation script with the new platform:

```bash
cd /path/to/your/project
~/coding/projects/specter/scripts/install-specter.sh --platform [new-platform]
# Then restart Claude Code
```

The installation will:
- Update `.specter/config.json` with new platform
- Regenerate all commands in `.claude/commands/` with new platform-specific tools
- Regenerate all agents in `.claude/agents/` with updated configurations

**Note:** Existing work (plans, specs) won't automatically migrate between platforms. You'll need to manually recreate them in the new platform if needed.
- There are plans to add a migration tool in the future to help with this.

## Troubleshooting

### Specter MCP Server Not Available

**Problem:** Specter doesn't appear in `/mcp list` output

**Symptoms:**
- `/mcp list` doesn't show "specter"
- Error: "MCP server 'specter' not found"
- Specter workflow commands not available

**Solution:**

1. **Verify Specter was registered correctly**
   ```bash
   claude mcp list
   ```

   Should show `specter` in the list of configured servers.

   To see full details:
   ```bash
   claude mcp get specter
   ```

2. **If Specter is missing, register it**
   ```bash
   claude mcp add --transport stdio specter -- uv run --directory /absolute/path/to/specter specter-server
   ```

   Replace `/absolute/path/to/specter` with your actual path:
   - ✅ Correct: `/Users/username/coding/projects/specter`
   - ❌ Wrong: `~/coding/projects/specter` (tilde won't expand)
   - ❌ Wrong: `../specter` (relative path won't work)

3. **Verify Specter repository exists and has dependencies**
   ```bash
   cd /path/to/specter  # Use the path from your installation
   ls -la  # Should show pyproject.toml, services/, etc.
   uv sync  # Re-install dependencies if needed
   ```

4. **Test Specter runs manually (optional)**
   ```bash
   cd /path/to/specter
   uv run specter-server
   ```

   Should start without errors. Press Ctrl+C to stop.

   **Note:** You may see a KeyboardInterrupt error when stopping - this is harmless and does not affect functionality.

5. **Verify uv is available**
   ```bash
   which uv
   uv --version
   ```

   If not found, install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

6. **Check Python version**
   ```bash
   python --version  # or python3 --version
   ```

   Must be Python 3.13 or higher. If lower, install Python 3.13+.

7. **Restart Claude Code**
   ```bash
   # Exit Claude Code completely
   # Restart:
   claude
   ```

8. **Verify MCP server is loaded**
   ```text
   /mcp list
   ```

**If still not working:**
- Remove and re-add the MCP server:
  ```bash
  claude mcp remove specter
  claude mcp add --transport stdio specter -- uv run --directory /absolute/path/to/specter specter-server
  ```
- Check Claude Code logs for errors (location varies by OS)
- Ensure no other process is using the same MCP server name

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

**Problem:** Specter commands don't appear or autocomplete

**Symptoms:**
- Typing `/specter-` doesn't autocomplete
- Error: "Command not found: /specter-plan"
- `.claude/commands/` directory is empty or missing files

**Solution:**

1. **Verify setup was completed**
   ```bash
   ls -la .claude/commands/specter-*.md
   ```

   Should show 5 files:
   - specter-plan.md
   - specter-roadmap.md
   - specter-spec.md
   - specter-build.md
   - specter-plan-conversation.md

2. **Check you're in the correct directory**
   ```bash
   pwd  # Should be your project directory
   ls .claude/  # Should exist
   ```

3. **If files are missing, re-run installation**
   ```bash
   ~/coding/projects/specter/scripts/install-specter.sh --platform [your-platform]
   # Then restart Claude Code
   ```

4. **Verify Specter MCP server is available**
   ```text
   /mcp list  # Should show "specter"
   ```

   If Specter MCP server is missing, see [Specter MCP Server Not Available](#specter-mcp-server-not-available) above.

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
- Re-run installation script: `~/path/to/specter/scripts/install-specter.sh`
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
   cat .specter/config/platform.json
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
   ls -la .specter/projects/

   # If missing, create it:
   mkdir -p .specter/projects/
   ```

5. **Check file permissions**
   ```bash
   ls -la .specter/
   # All directories should be writable (755 or 775 permissions)

   # Fix if needed:
   chmod -R 755 .specter/
   ```

6. **Re-run installation if configuration is corrupted**
   ```bash
   ~/coding/projects/specter/scripts/install-specter.sh --platform [platform]
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

### Installation Script Fails

**Problem:** `install-specter.sh` script errors or doesn't complete

**Symptoms:**
- Permission denied errors
- Script not found
- Curl download fails (for remote installation)

**Solution:**

1. **For local script execution:**
   ```bash
   # Verify script exists
   ls -la ~/coding/projects/specter/scripts/install-specter.sh

   # Make executable if needed
   chmod +x ~/coding/projects/specter/scripts/install-specter.sh

   # Run with explicit path
   ~/coding/projects/specter/scripts/install-specter.sh --platform markdown
   ```

2. **For remote curl installation (public repos only):**
   ```bash
   # Verify you have curl
   which curl
   curl --version

   # Test URL is accessible
   curl -I https://raw.githubusercontent.com/mmcclatchy/specter/main/scripts/install-specter.sh

   # Should return "200 OK"
   ```

3. **For private repositories:**

   Remote curl installation won't work for private repos. Use local installation or bootstrap method instead.

4. **Alternative: Use bootstrap method**
   ```bash
   cd /path/to/your/project
   claude
   ```

   ```text
   Install the Specter bootstrap files for this project
   ```

---

### Python Version Errors

**Problem:** Python version compatibility issues

**Symptoms:**
- Error: "Python 3.13+ required"
- Syntax errors in Specter code
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
   cd /path/to/specter
   uv python list
   uv sync  # Re-sync with correct Python version
   ```

4. **Specify Python version if needed**

   If multiple Python versions exist, you can specify Python 3.13 when registering:
   ```bash
   claude mcp remove specter  # Remove existing registration
   claude mcp add --transport stdio specter -- uv run --python 3.13 --directory /absolute/path/to/specter specter-server
   ```

## Best Practices

### Strategic Planning

**Do:**
- Use `/specter-plan` which will automatically guide you through conversational discovery
- Be specific about business objectives when answering questions
- Include constraints and limitations
- Provide context about users and use cases

**Don't:**
- Skip strategic planning for large features
- Mix technical details with business objectives
- Rush through refinement loops
- Call `/specter-plan-conversation` directly (it's used internally by `/specter-plan`)

### Roadmap Planning

**Do:**
- Use `/specter-roadmap` for projects that benefit from phased decomposition
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
export SPECTER_PLAN_THRESHOLD=80
export SPECTER_SPEC_THRESHOLD=85
export SPECTER_BUILD_THRESHOLD=90
```

### Multi-Phase Projects

For complex projects:

1. Use `/specter-roadmap` for overall structure
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

**Q: Can I use Specter without an external platform?**
A: Yes, use the Markdown platform for local file-based workflows.

**Q: Can I switch platforms after setup?**
A: Yes, but you'll need to delete configuration and re-run setup. Existing work won't automatically migrate.

**Q: Do I need all the generated agents?**
A: Yes, agents work together in refinement loops. Removing agents may break workflows.

**Q: Can I customize the templates?**
A: Templates are generated fresh each time. Customization requires modifying the Specter MCP server code.

**Q: How do I update Specter?**
A: Pull latest changes from repository and re-run installation script. Existing projects won't be affected.

## Next Steps

1. **Install Specter** using the installation script
2. **Restart Claude Code** to load workflow commands
3. **Start planning** with `/specter-plan`
4. **Breakdown the plan into specifications** with `/specter-roadmap`
5. **Design and Refine specifications** with `/specter-spec`
6. **Implement features** with `/specter-build`
