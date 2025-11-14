#!/usr/bin/env python3
"""Add project_path documentation to all agent templates."""

import re
from pathlib import Path


def update_agent_inputs(content: str) -> str:
    # Find INPUTS section and add project_path if not present
    if 'INPUTS:' in content and 'project_path:' not in content:
        pattern = r'(INPUTS:[^\n]*\n)'
        replacement = r'\1- project_path: Project directory path (automatically provided by calling command)\n\n**Important**: All `mcp__specter__*` tool calls must include project_path as the first parameter.\n\n'
        content = re.sub(pattern, replacement, content, count=1)

    return content


def main() -> None:
    agents_dir = Path(__file__).parent.parent / 'services' / 'templates' / 'agents'

    print('Updating agent templates with project_path documentation...\n')

    for file_path in sorted(agents_dir.glob('*.py')):
        if file_path.name == '__init__.py':
            continue

        content = file_path.read_text()
        original = content

        # Check if agent uses MCP tools
        if 'mcp__specter__' not in content:
            print(f'  - Skipped {file_path.name} (no MCP calls)')
            continue

        # Update INPUTS section
        content = update_agent_inputs(content)

        if content != original:
            file_path.write_text(content)
            print(f'  ✓ Updated {file_path.name}')
        else:
            print(f'  - Skipped {file_path.name} (already has project_path)')

    print('\n✅ Agent template updates complete!')
    print('\nNote: Claude will automatically pass project_path when calling these agents.')
    print("The tool signatures require it, and we've documented it in INPUTS.")


if __name__ == '__main__':
    main()
