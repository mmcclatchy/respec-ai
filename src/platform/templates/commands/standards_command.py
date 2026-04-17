from src.platform.models import StandardsCommandTools


def generate_standards_command_template(tools: StandardsCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [language] | render [language]
description: Author project coding standards from canonical TOML templates
---

# {tools.standards_command_name} Command

## Purpose
Maintain canonical TOML standards and optionally render a derived LLM-authored guide.
Canonical source of truth is always `.respec-ai/config/standards/{{language}}.toml`.

## Workflow

1. Parse command arguments:
```text
IF first argument == "render":
  MODE = "render"
  LANGUAGE = second argument (required)
ELSE:
  MODE = "author"
  LANGUAGE = first argument (default: primary language from .respec-ai/config/stack.toml)
```

2. Resolve canonical TOML target:
```text
TARGET_TOML = .respec-ai/config/standards/{{LANGUAGE}}.toml
If TARGET_TOML doesn't exist:
  Inform user to run: respec-ai standards init {{LANGUAGE}}
  Exit.
```

3. Branch by mode:
```text
IF MODE == "author": run AUTHOR FLOW
IF MODE == "render": run RENDER FLOW
```

AUTHOR FLOW

4. Load target TOML and inspect incomplete sections:
```text
INCOMPLETE means:
- empty command values under [commands]
- any rules section with zero entries
- entries that contain TODO placeholders
```

5. For each incomplete section, ask user for preference using AskUserQuestion:
```text
Prompt should ask for explicit rule direction.
Allowed fallback answer: "no_preference" (or "no-preference").
```

6. Rewrite each populated section as authoritative agent-style rules:
```text
- Use imperative tone ("MUST", "MUST NOT", "DO NOT")
- Add concrete "CORRECT"/"WRONG" examples when user provides enough context
- Keep rules concise and enforceable
```

7. Save updated TOML to TARGET_TOML.

8. Final output:
```text
Standards template updated: .respec-ai/config/standards/{{LANGUAGE}}.toml
Next steps:
1) Run: respec-ai standards validate
2) Optional: run respec-standards render {{LANGUAGE}} to generate a derived guide
```

RENDER FLOW

4. Read canonical TOML (`TARGET_TOML`) and extract:
```text
- [commands] entries
- [testing] entries
- [rules] entries
```

5. Synthesize a derived standards guide markdown:
```text
TARGET_GUIDE = .respec-ai/config/standards/guides/{{LANGUAGE}}.md
Ensure directory exists: .respec-ai/config/standards/guides/

Guide requirements:
- Start with a clear canonical-source notice:
  "This guide is derived from TOML. TOML remains authoritative."
- Convert standards into imperative language ("MUST", "MUST NOT", "DO NOT")
- Include concise rationale where helpful
- Add concrete CORRECT/WRONG code examples for major rules
- Include commands section (test, coverage, type_check, lint)
```

6. Write guide to `TARGET_GUIDE`.

7. Final output:
```text
Derived standards guide rendered: .respec-ai/config/standards/guides/{{LANGUAGE}}.md
Canonical source remains: .respec-ai/config/standards/{{LANGUAGE}}.toml
```
"""
