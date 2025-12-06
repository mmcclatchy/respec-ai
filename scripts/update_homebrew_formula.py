#!/usr/bin/env python3
"""Update Homebrew formula with new version and regenerated resources."""

import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def generate_resources() -> str:
    # Generate resources for all dependencies (direct + transitive)
    # Use poet with all packages at once to get complete dependency tree
    deps = ['pydantic', 'pydantic-settings', 'rich', 'markdown-it-py', 'docker']

    try:
        # Build poet command with --also flags for all dependencies
        cmd = ['poet'] + deps
        output = run_command(cmd)

        # Extract resource blocks (remove warnings/comments)
        lines = output.split('\n')
        resource_lines = [line for line in lines if not line.strip().startswith('/')]
        return '\n'.join(resource_lines)
    except subprocess.CalledProcessError as e:
        print(f'Error: Failed to generate resources: {e}', file=sys.stderr)
        # Return empty string to avoid breaking the formula
        return ''


def update_formula(formula_path: Path, version: str, url: str, sha256: str) -> None:
    content = formula_path.read_text()

    # Update main package URL
    content = re.sub(
        r'url "https://test-files\.pythonhosted\.org/packages/.*/respec_ai-.*\.tar\.gz"', f'url "{url}"', content
    )

    # Update main package SHA256 (first occurrence after URL)
    content = re.sub(
        r'(url "https://test-files\.pythonhosted\.org/packages/.*?\.tar\.gz"\s+)sha256 ".*?"',
        rf'\1sha256 "{sha256}"',
        content,
        count=1,
    )

    # Update test version assertion
    content = re.sub(r'assert_match ".*?", shell_output', f'assert_match "{version}", shell_output', content)

    # Generate new resource blocks
    print('Generating resource blocks...', file=sys.stderr)
    resources = generate_resources()

    # Replace resource blocks section (between depends_on and def install)
    # Support both "python" and "python@X.Y" patterns
    pattern = r'(depends_on "python(?:@[\d.]+)?".+?\n)(.*?)(\n\s+def install)'
    replacement = rf'\1\n  {resources}\3'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    formula_path.write_text(content)
    print(f'Updated formula to version {version}', file=sys.stderr)


def main() -> None:
    if len(sys.argv) != 5:
        print('Usage: update_homebrew_formula.py <formula_path> <version> <url> <sha256>')
        sys.exit(1)

    formula_path = Path(sys.argv[1])
    version = sys.argv[2]
    url = sys.argv[3]
    sha256 = sys.argv[4]

    if not formula_path.exists():
        print(f'Error: Formula file not found: {formula_path}')
        sys.exit(1)

    update_formula(formula_path, version, url, sha256)


if __name__ == '__main__':
    main()
