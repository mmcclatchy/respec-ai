# Windows Compatibility Investigation

Status: **Investigation needed** — issues identified, not yet fully scoped or resolved.

## Background

The respec-ai codebase has an inherent bias toward Unix operating systems. Windows users may run respec-ai through PowerShell (OpenCode) or Git Bash (Claude Code and OpenCode). This document catalogs identified issues and areas to explore.

## Python CLI Code (Low Risk)

The Python CLI code properly uses `Path.home()` and `Path` objects for all config paths:

- `src/cli/config/global_config.py:6` — `Path.home() / '.config' / 'respec-ai'`
- `src/cli/config/claude_config.py:6-8` — `Path.home() / '.claude' / 'config.json'`
- `src/cli/config/ide_constants.py:11` — `Path.home() / '.claude' / 'config.json'`

These resolve correctly on Windows (e.g., `C:\Users\<name>\.config\respec-ai\`).

## Template Instructions (Medium Risk)

Templates are LLM instructions — the agent interprets them and passes paths to tools (Read, Write, Glob, Bash). The tools are implemented by Claude Code/OpenCode. Whether path issues manifest depends on how those tool implementations handle different path formats on Windows.

### Areas to Investigate

#### 1. plans_dir tilde strings (15+ locations)

`plans_dir` defaults to `'~/.claude/plans'` as a string literal, passed through the strategy chain and embedded in templates. The agent uses this in tool calls like `Read(~/.claude/plans/foo.md)`.

**Question**: Do Claude Code and OpenCode tool implementations expand `~` on Windows? Does this work in PowerShell? In Git Bash?

**Files to check**:

- `src/platform/template_helpers.py` (lines 130, 210, 572, 693, 1216) — factory function defaults
- `src/platform/command_strategies/base.py` (lines 28, 40) — strategy defaults
- All 7 concrete strategies in `src/platform/command_strategies/` — each passes `plans_dir`
- `src/platform/tui_adapters/claude_code.py:95` — returns `'~/.claude/plans'`
- `src/platform/tui_adapters/opencode.py:130` — returns `'.opencode/plans'`

#### 2. Bash commands in templates

Several templates use Unix shell commands that don't exist or behave differently on Windows PowerShell:

- `plan_command.py:141` — `find {plans_dir} -name "*.md" -mtime -7 -type f 2>/dev/null | head -5`
- Various agent templates use `Bash` for `grep`, `wc`, counting operations

**PowerShell equivalents needed**: `Get-ChildItem` for `find`, `Select-Object -First 5` for `head`, etc.

**Question**: Does Claude Code on Windows use Git Bash as its shell (which would have GNU `find`)? Does OpenCode use the system shell (PowerShell)?

#### 3. path_constants.py f-string concatenation

`src/platform/path_constants.py` builds paths using f-strings with `/`:

```python
f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{plan_name}/...'
```

These produce forward-slash paths that are passed to tools. Forward slashes generally work on Windows in Python's `Path`, but may not work in all tool contexts.

**Files to check**: `src/platform/path_constants.py` (lines 17, 24, 35, 40-41)

#### 4. .respec-ai/ relative paths in templates (38+ instances)

All command and agent templates use forward-slash relative paths:

- `.respec-ai/plans/{PLAN_NAME}/references/{REFERENCE_FILENAME}`
- `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/tasks/{TASK_NAME}.md`
- `.respec-ai/config/stack.md`
- `.respec-ai/config.json`

**Question**: Do Claude Code/OpenCode tools resolve project-relative paths with forward slashes on Windows?

#### 5. Step 1.5 plan file discovery

The `Bash: find` command in Step 1.5 is completely incompatible with PowerShell. This needs a platform-aware alternative — either:

- Use `Glob` tool instead of `Bash: find` (preferred — tools handle cross-platform)
- Detect shell type and use appropriate command

#### 6. OpenCode shell environment

**Question**: What shell does OpenCode use for Bash tool calls on Windows? If it uses PowerShell natively, all `Bash` tool calls with Unix syntax will fail. If it uses WSL or Git Bash, they may work.

## Resolved Issues

### Step 1.7 external path detection (Fixed)

Original check `starts with "~" or "/"` only detected Unix absolute paths. Updated to also detect Windows drive letters (`C:\`, `D:\`) and UNC paths (`\\server\...`).

## Recommended Investigation Approach

1. **Test on Windows**: Set up a Windows dev environment with both Claude Code (Git Bash) and OpenCode (PowerShell) to empirically test tool behavior
2. **Check tool source**: Review Claude Code and OpenCode documentation or source for how Read/Write/Glob/Bash tools handle path formats on Windows
3. **Prioritize by user base**: If Windows users primarily use Git Bash, many issues may be non-issues; if PowerShell is common, the Bash command incompatibility is critical
4. **Glob over Bash**: Where possible, replace `Bash: find/grep/wc` with dedicated tools (Glob, Grep, Read) which are more likely to be cross-platform
