#!/usr/bin/env python3
"""
Update all command and agent templates to include project_path parameter in MCP calls.

This script:
1. Adds PROJECT_PATH initialization to command templates
2. Updates all mcp__spec-ai__* calls to include project_path parameter
3. Documents project_path in agent template INPUTS sections
"""

import re
from pathlib import Path


def update_command_template(file_path: Path) -> tuple[bool, str]:
    content = file_path.read_text()
    original = content

    # Add PROJECT_PATH initialization if not present
    if 'PROJECT_PATH' not in content and 'pwd' not in content:
        # Find the first ## heading after the --- block
        pattern = r'(---\n\n# .*?\n\n)(##)'
        replacement = r'\1## Step 0: Initialize Project Context\n\nCapture the current project directory for multi-project support:\n\n```bash\npwd\n```\n\nStore the result as PROJECT_PATH. This will be passed to all SpecAI MCP tools.\n\n```text\nPROJECT_PATH = [result of pwd command]\n```\n\n\2'
        content = re.sub(pattern, replacement, content, count=1)

    # Update MCP calls - pattern: mcp__spec-ai__tool_name(params)
    # We need to add project_path=PROJECT_PATH as first parameter

    # Pattern 1: Simple calls with just one param
    content = re.sub(r'mcp__spec-ai__(\w+)\(([^,)]+)\)', r'mcp__spec-ai__\1(project_path=PROJECT_PATH, \2)', content)

    # Pattern 2: Calls with multiple params
    content = re.sub(
        r'mcp__spec-ai__(\w+)\(([^)]+, [^)]+)\)', r'mcp__spec-ai__\1(project_path=PROJECT_PATH, \2)', content
    )

    # Pattern 3: Calls with no params
    content = re.sub(r'mcp__spec-ai__(\w+)\(\)', r'mcp__spec-ai__\1(project_path=PROJECT_PATH)', content)

    # Fix double project_path if we already added it
    content = re.sub(r'project_path=PROJECT_PATH, project_path=PROJECT_PATH', 'project_path=PROJECT_PATH', content)

    changed = content != original
    return changed, content


def update_agent_template(file_path: Path) -> tuple[bool, str]:
    content = file_path.read_text()
    original = content

    # Add project_path documentation to INPUTS section if mcp__spec-ai__ calls exist
    if 'mcp__spec-ai__' in content and 'project_path' not in content:
        # Find INPUTS section
        pattern = r'(INPUTS:.*?\n)'
        if re.search(pattern, content):
            replacement = r'\1- project_path: Project directory path (provided by calling command/agent)\n'
            content = re.sub(pattern, replacement, content, count=1)

    # Update MCP calls to include project_path
    content = re.sub(r'mcp__spec-ai__(\w+)\(([^,)]+)\)', r'mcp__spec-ai__\1(project_path, \2)', content)

    content = re.sub(r'mcp__spec-ai__(\w+)\(([^)]+, [^)]+)\)', r'mcp__spec-ai__\1(project_path, \2)', content)

    content = re.sub(r'mcp__spec-ai__(\w+)\(\)', r'mcp__spec-ai__\1(project_path)', content)

    # Fix doubles
    content = re.sub(r'project_path, project_path', 'project_path', content)

    changed = content != original
    return changed, content


def main() -> None:
    project_root = Path(__file__).parent.parent

    commands_dir = project_root / 'services' / 'templates' / 'commands'
    agents_dir = project_root / 'services' / 'templates' / 'agents'

    print('Updating command templates...')
    for file_path in commands_dir.glob('*.py'):
        if file_path.name == '__init__.py':
            continue

        changed, new_content = update_command_template(file_path)
        if changed:
            file_path.write_text(new_content)
            print(f'  ✓ Updated {file_path.name}')
        else:
            print(f'  - Skipped {file_path.name} (no changes needed)')

    print('\nUpdating agent templates...')
    for file_path in agents_dir.glob('*.py'):
        if file_path.name == '__init__.py':
            continue

        changed, new_content = update_agent_template(file_path)
        if changed:
            file_path.write_text(new_content)
            print(f'  ✓ Updated {file_path.name}')
        else:
            print(f'  - Skipped {file_path.name} (no changes needed)')

    print('\n✅ Template updates complete!')


if __name__ == '__main__':
    main()
