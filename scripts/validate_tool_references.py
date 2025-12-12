"""Validate that all MCP tool references use correct tool names."""

import re
import sys
from pathlib import Path


# List of legacy tools that should NOT appear
LEGACY_TOOLS = [
    'store_phase',
    'get_phase',
    'get_phase_markdown',
    'update_phase',
    'list_phases',
    'delete_phase',
    'link_loop_to_phase',
    'resolve_phase_name',
    'store_build_plan',
    'get_build_plan',
    'get_build_plan_markdown',
    'store_phase',
    'get_phase_markdown',
    'list_phases',
    'delete_phase',
    'store_current_objective_feedback',
    'get_previous_objective_feedback',
]


def scan_file(file_path: Path) -> list[str]:
    """Scan a file for legacy tool references.

    Args:
        file_path: Path to file to scan

    Returns:
        List of violation messages (empty if no issues found)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return [f'{file_path}: Error reading file - {e}']

    violations = []

    for tool in LEGACY_TOOLS:
        pattern = rf'mcp__respec-ai__{tool}'
        matches = list(re.finditer(pattern, content))
        for match in matches:
            line_num = content[: match.start()].count('\n') + 1
            violations.append(f'{file_path}:{line_num} - Found legacy tool: {tool}')

    return violations


def validate_codebase() -> bool:
    """Scan entire codebase for legacy tool references.

    Returns:
        True if validation passed (no legacy tools found), False otherwise
    """
    violations = []
    project_root = Path(__file__).parent.parent

    # Scan template generators
    templates_dir = project_root / 'src' / 'platform' / 'templates'
    if templates_dir.exists():
        for py_file in templates_dir.rglob('*.py'):
            violations.extend(scan_file(py_file))

    # Scan models.py (computed fields)
    models_file = project_root / 'src' / 'platform' / 'models.py'
    if models_file.exists():
        violations.extend(scan_file(models_file))

    # Scan template helpers
    helpers_file = project_root / 'src' / 'platform' / 'template_helpers.py'
    if helpers_file.exists():
        violations.extend(scan_file(helpers_file))

    # Scan tool enums
    enums_file = project_root / 'src' / 'platform' / 'tool_enums.py'
    if enums_file.exists():
        violations.extend(scan_file(enums_file))

    # Scan generated templates (for verification)
    claude_dir = project_root / '.claude'
    if claude_dir.exists():
        for md_file in claude_dir.rglob('*.md'):
            violations.extend(scan_file(md_file))

    if violations:
        print('❌ Found legacy tool references:')
        for v in violations:
            print(f'  {v}')
        print()
        print('These tools no longer exist. Use the document tools instead:')
        print("  - store_phase → store_document(doc_type='phase', ...)")
        print("  - get_phase → get_document(doc_type='phase', ...)")
        print("  - update_phase → update_document(doc_type='phase', ...)")
        return False
    else:
        print('✅ No legacy tool references found')
        return True


if __name__ == '__main__':
    success = validate_codebase()
    sys.exit(0 if success else 1)
