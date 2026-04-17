from src.platform.models import StandardsCommandTools


def generate_standards_command_template(tools: StandardsCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [optional: language|all]
description: Render standards guides from canonical TOML templates
---

# {tools.standards_command_name} Command

## Purpose
Render derived standards guides from canonical TOML standards.
Canonical source of truth is always `.respec-ai/config/standards/{{language}}.toml`.
This command MUST NOT edit canonical TOML files.

## Workflow

1. Parse command arguments:
```text
RAW_ARGS = trimmed argument tokens

Compatibility:
- If RAW_ARGS[0] == "render", treat RAW_ARGS[1] as target.
- Otherwise, treat RAW_ARGS[0] as target.

TARGET = normalized lowercase target token (optional: language or "all")
```

2. Resolve target language set:
```text
STANDARD_FILES = Glob(.respec-ai/config/standards/*.toml)
LANGUAGE_FILES = STANDARD_FILES excluding universal.toml
AVAILABLE_LANGUAGES = filename stems from LANGUAGE_FILES

If AVAILABLE_LANGUAGES is empty:
  Stop and return structured error:
  "standards_languages_missing: no language TOML files found under .respec-ai/config/standards/; run respec-ai standards init <language...>."

IF TARGET is missing:
  MUST call AskUserQuestion to select one language or "all".
  MUST NOT infer or auto-select a default target, even when only one language exists.
  AskUserQuestion:
    Header: "Standards Target"
    Question: "Select standards target language or all."
    Options:
      1) one language (pick from AVAILABLE_LANGUAGES)
      2) all languages
  TARGET = selected value

If AskUserQuestion is unavailable:
  Stop and return structured error:
  "standards_target_selection_unavailable: missing AskUserQuestion tool; cannot continue without explicit target selection."

IF TARGET == "all":
  TARGET_LANGUAGES = AVAILABLE_LANGUAGES
ELSE:
  If TARGET not in AVAILABLE_LANGUAGES:
    Stop and return structured error:
    "standards_language_invalid: target '{{TARGET}}' not found; available={{AVAILABLE_LANGUAGES}}."
  TARGET_LANGUAGES = [TARGET]
```

3. For each language in TARGET_LANGUAGES, render guide:
```text
TARGET_TOML = .respec-ai/config/standards/{{LANGUAGE}}.toml
TARGET_GUIDE = .respec-ai/config/standards/guides/{{LANGUAGE}}.md
Ensure directory exists: .respec-ai/config/standards/guides/

Read TARGET_TOML.
Extract supported sections when present:
- [commands]
- [testing]
- [rules]

Guide requirements:
- Start with a clear canonical-source notice:
  "This guide is derived from TOML. TOML remains authoritative."
- Convert standards into imperative language ("MUST", "MUST NOT", "DO NOT")
- Include concise rationale where helpful
- Add concrete CORRECT/WRONG code examples for major rules
- Include sections only when corresponding TOML data exists
- If a section is missing in TOML, omit it from the guide (do not invent values)
```

4. Write guide to `TARGET_GUIDE`.

5. Final output:
```text
Derived standards guides rendered for: {{TARGET_LANGUAGES}}
Canonical source remains: .respec-ai/config/standards/{{LANGUAGE}}.toml for each language
```
"""
