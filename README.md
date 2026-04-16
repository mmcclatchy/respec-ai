# `respec-ai`

Agentic, phase-driven workflow tooling for AI-assisted software delivery.

`respec-ai` bootstraps command/agent templates for Claude Code, OpenCode, and Codex, and runs a meta MCP server used by generated workflows.

## Quick Start

Prerequisites:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/)

Install:

```bash
uv tool install git+https://github.com/mmcclatchy/respec-ai.git
```

Initialize inside your project:

```bash
cd /path/to/your/project
respec-ai init -p markdown
```

### Standards Preflight (Recommended)

Run this once before running workflow commands.

1. Generate standards templates:

```bash
respec-ai standards init
```

2. In your TUI, run `respec-standards` for each language you care about.
   - Claude Code / OpenCode: `/respec-standards python`
   - Codex: `$respec-standards python`

3. Validate canonical config:

```bash
respec-ai standards validate
```

4. Start workflows:
   - `/respec-plan ...`
   - `/respec-phase ...`
   - `/respec-code ...`

`stack.toml` and `standards/*.toml` are canonical. There are no markdown mirror config files.

## TUI Support

| TUI | Init Flag | Generated Artifacts |
|---|---|---|
| Claude Code | *(default)* | `.claude/commands/*.md`, `.claude/agents/*.md` |
| OpenCode | `--tui opencode` | `opencode.json`, `.opencode/prompts/commands/*.md`, `.opencode/prompts/agents/*.md` |
| Codex | `--tui codex` | `.codex/skills/*/SKILL.md`, `.codex/agents/*-agent.toml` |

## Platform Support

| Platform | Integration |
|---|---|
| Linear | MCP API |
| GitHub | MCP API |
| Markdown | Local files |

## Core Workflows

- `respec-plan`: strategic plan generation and refinement
- `respec-roadmap`: phase roadmap generation
- `respec-phase`: technical phase specification
- `respec-task`: implementation task breakdown
- `respec-code`: implementation + review loops
- `respec-patch`: amendment workflow for existing phases
- `respec-standards`: standards authoring from TOML templates

## Codex Command Usage Tiers

- Preflight:
  - `respec-standards` (run before `respec-plan`, `respec-phase`, `respec-code`, `respec-patch`)
- Primary:
  - `respec-plan`, `respec-phase`, `respec-code`, `respec-patch`
- Secondary:
  - `respec-roadmap` (typically invoked by `respec-plan`)
  - `respec-task` (typically invoked by `respec-phase`)
- Internal:
  - `respec-plan-conversation` (used by `respec-plan`, not a direct entry point)

## Model Configuration

Configure model tiers after init (or reconfigure anytime):

```bash
respec-ai models opencode
respec-ai models codex
```

Optional benchmark/enrichment keys:

```bash
respec-ai models opencode --aa-key YOUR_KEY --exa-key YOUR_KEY
```

## Useful Commands

```bash
respec-ai status
respec-ai validate
respec-ai regenerate
respec-ai register-mcp
respec-ai unregister-mcp
respec-ai update
```

## Documentation

- [CLI Guide](docs/CLI_GUIDE.md)
- [Workflows Guide](docs/WORKFLOWS.md)
- [Architecture Guide](docs/ARCHITECTURE.md)

## Requirements

- Python 3.11+
- Docker / Docker Desktop
- uv
- Claude Code, OpenCode, or Codex

## License

Source Available

## Support

- [GitHub Issues](https://github.com/mmcclatchy/respec-ai/issues)
