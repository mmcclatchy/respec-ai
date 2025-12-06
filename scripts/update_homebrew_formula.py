#!/usr/bin/env python3
"""Update Homebrew formula with new version."""

import re
import sys
from pathlib import Path


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

    # Ensure install method stays simple (no resource blocks needed)
    # This pattern catches old virtualenv_install_with_resources and replaces with custom method
    old_install_pattern = r'def install\s+virtualenv_install_with_resources\s+end'
    new_install = """def install
    # Create virtualenv
    venv = virtualenv_create(libexec, "python3")

    # Install package with dependencies (pip fetches dependencies from PyPI as wheels)
    # Must use direct system call instead of pip_install_and_link to avoid --no-deps flag
    system libexec/"bin/pip", "install", "--verbose", buildpath

    # Create symlink to bin
    bin.install_symlink libexec/"bin/respec-ai"
  end"""

    if re.search(old_install_pattern, content, re.DOTALL):
        content = re.sub(old_install_pattern, new_install, content, re.DOTALL)

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
