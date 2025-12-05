#!/usr/bin/env python3
"""Release script for respec-ai project maintainers.

Creates a new release by:
1. Bumping version in pyproject.toml
2. Creating git commit and tag
3. Pushing to origin

Usage:
    python scripts/release.py major
    python scripts/release.py minor
    python scripts/release.py patch
    python scripts/release.py patch --yes
"""

import re
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path


def run_command(cmd: list[str], error_msg: str) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f'❌ {error_msg}', file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def check_working_directory_clean() -> bool:
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            check=True,
            capture_output=True,
            text=True,
        )
        return not result.stdout.strip()
    except subprocess.CalledProcessError:
        return False


def get_current_version(pyproject_path: Path) -> str | None:
    content = pyproject_path.read_text(encoding='utf-8')
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None


def calculate_new_version(current: str, bump_type: str) -> str:
    major, minor, patch = map(int, current.split('.'))

    if bump_type == 'major':
        return f'{major + 1}.0.0'
    elif bump_type == 'minor':
        return f'{major}.{minor + 1}.0'
    else:  # patch
        return f'{major}.{minor}.{patch + 1}'


def update_version_in_file(pyproject_path: Path, old_version: str, new_version: str) -> None:
    content = pyproject_path.read_text(encoding='utf-8')
    updated = re.sub(
        rf'^version = "{re.escape(old_version)}"',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(updated, encoding='utf-8')


def main() -> int:
    """Create a new release with version bump.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = ArgumentParser(description='Create a new release with version bump')
    parser.add_argument(
        'bump_type',
        choices=['major', 'minor', 'patch'],
        help='Version bump type (major, minor, or patch)',
    )
    parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        help='Skip confirmation prompt',
    )
    args = parser.parse_args()

    pyproject_path = Path.cwd() / 'pyproject.toml'

    if not pyproject_path.exists():
        print('❌ pyproject.toml not found in current directory', file=sys.stderr)
        return 1

    if not check_working_directory_clean():
        print('❌ Working directory is not clean', file=sys.stderr)
        print('⚠️  Commit or stash changes before creating a release', file=sys.stderr)
        subprocess.run(['git', 'status', '--short'])
        return 1

    current_version = get_current_version(pyproject_path)
    if not current_version:
        print('❌ Could not find version in pyproject.toml', file=sys.stderr)
        return 1

    new_version = calculate_new_version(current_version, args.bump_type)

    print(f'Current version: {current_version}')
    print(f'New version: {new_version}')

    if not args.yes:
        response = input(f'\nProceed with release {new_version}? (y/N): ')
        if response.lower() not in ('y', 'yes'):
            print('⚠️  Release cancelled')
            return 0

    try:
        update_version_in_file(pyproject_path, current_version, new_version)
        print(f'✓ Updated pyproject.toml to version {new_version}')

        run_command(['git', 'add', 'pyproject.toml'], 'Failed to stage pyproject.toml')

        run_command(
            ['git', 'commit', '-m', f'Bump version to {new_version}'],
            'Failed to commit version bump',
        )

        run_command(['git', 'tag', f'v{new_version}'], f'Failed to create tag v{new_version}')

        print('Pushing to origin...')
        run_command(['git', 'push', 'origin', 'main'], 'Failed to push to origin main')
        run_command(['git', 'push', 'origin', f'v{new_version}'], f'Failed to push tag v{new_version}')

        print(f'\n✓ Release {new_version} complete!')
        print('  - Committed version bump')
        print(f'  - Created tag v{new_version}')
        print('  - Pushed to origin')

        return 0

    except Exception as e:
        print(f'❌ Release failed: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
