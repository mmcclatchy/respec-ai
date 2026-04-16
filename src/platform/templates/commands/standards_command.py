from src.platform.models import StandardsCommandTools


def generate_standards_command_template(tools: StandardsCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [language]
description: Author project coding standards from canonical TOML templates
---

# {tools.standards_command_name} Command

## Purpose
Fill out `.respec-ai/config/standards/{{language}}.toml` with concrete, imperative coding standards.
This command treats TOML as canonical source of truth.

## Workflow

1. Parse command argument:
```text
LANGUAGE = first argument (default: primary language from .respec-ai/config/stack.toml)
```

2. Resolve target file:
```text
TARGET_FILE = .respec-ai/config/standards/{{LANGUAGE}}.toml
If file doesn't exist:
  Inform user to run: respec-ai standards init --language {{LANGUAGE}}
  Exit.
```

3. Load target template and inspect incomplete sections:
```text
INCOMPLETE means:
- empty command values under [commands]
- any rules section with zero entries
- entries that contain TODO placeholders
```

4. For each incomplete section, ask user for preference using AskUserQuestion:
```text
Prompt should ask for explicit rule direction.
Allowed fallback answer: "no_preference" (or "no-preference").
```

5. Rewrite each populated section as authoritative agent-style rules:
```text
- Use imperative tone ("MUST", "MUST NOT", "DO NOT")
- Add concrete "CORRECT"/"WRONG" examples when user provides enough context
- Keep rules concise and enforceable
```

6. Save updated TOML to TARGET_FILE.

7. Final output:
```text
Standards template updated: .respec-ai/config/standards/{{LANGUAGE}}.toml
Next steps:
1) Run: respec-ai standards validate
```
"""
