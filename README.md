# `respec-ai`

AI-assisted delivery often breaks down when vague requirements move to code before constraints are explicit: plans drift, documents desync, and teams burn cycles on ad hoc prompt retries to close quality gaps.

`respec-ai` applies spec-driven development with MCP-orchestrated agentic reflection loops:
- `/respec-plan` turns ambiguity into a measurable plan
- `/respec-roadmap` decomposes that plan into phases
- `/respec-phase` defines system design and synthesizes best-practice research via `best-practices-rag`
- `/respec-task` generates implementation-grade task specs
- `/respec-code` plus `/respec-patch` run TDD-first implementation and review against those specs and project standards set by the user

`best-practices-rag` addresses a common LLM quality problem: code that works but is outdated, non-idiomatic, or inconsistently applied for a given stack. It queries a curated Neo4j knowledge graph first to reinforce proven patterns (including ones already in model training), performs external gap-fill research only when coverage is missing or stale, stores synthesized results back to the graph, and reuses them in future runs.

For command behavior and current workflow status details, see [docs/WORKFLOWS.md](docs/WORKFLOWS.md).

## Quick Start

Prerequisites:
- docker (Linux) or [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac and Windows)
- [uv](https://docs.astral.sh/uv/)

Install `respec-ai`:

```bash
uv tool install git+https://github.com/mmcclatchy/respec-ai.git
```

Initialize inside your project:

```bash
cd /path/to/your/project
respec-ai init -p markdown --tui {claude-code\|codex\|opencode\|}
```

### Standards Preflight (Recommended)

Run this once before running workflow commands.

- Generate standards templates:

```bash
respec-ai standards init python typescript
```
- Pass one or more languages as space-delimited arguments.
- Only the languages you pass are generated.
- Generated TOMLs are prefilled with starter best-practice defaults.

- In your TUI, run `respec-standards` for each language you care about to render derived guides from TOML.
- On TUIs with interactive prompt support, running `respec-standards` with no arguments prompts for target selection (language or `all`).
- On TUIs without interactive prompt support, pass an explicit target: `respec-standards <language>` or `respec-standards all`.
- Claude Code / OpenCode: `/respec-standards python`
- Claude Code / OpenCode (all): `/respec-standards all`
- Codex: `$respec-standards python`
- Codex (all): `$respec-standards all`

- Validate canonical config:

```bash
respec-ai standards validate
```

- Start workflows:
- `/respec-plan ...`
- `/respec-phase ...`
- `/respec-code ...`

`stack.toml` and `standards/*.toml` are canonical.
Optional `standards/guides/*.md` files are derived guidance artifacts and non-canonical.

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
- `respec-standards`: render derived standards guides from canonical TOML templates

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

- `respec-ai status` - Quick health check for install, config, and runtime state so you can spot setup drift before running workflows.
- `respec-ai validate` - Verifies project artifacts and configuration consistency to catch structural issues early.
- `respec-ai regenerate` - Rebuilds generated agents/commands after template, config, or version changes so runtime behavior stays aligned.
- `respec-ai register-mcp` - Registers MCP endpoints with your TUI so workflow tools are available to agents.
- `respec-ai unregister-mcp` - Cleans up MCP registration when uninstalling, troubleshooting, or reconfiguring environments.
- `respec-ai update` - Upgrades CLI/server components and refreshes runtime dependencies to keep tooling current and compatible.

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
