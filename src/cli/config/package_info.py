import subprocess
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path


import src


class PackageInfoError(Exception):
    pass


def get_package_installation_path() -> Path:
    """Get absolute path to installed respec-ai package.

    Uses Python module introspection to find where the package is installed.
    Works with:
    - uv-managed virtual environments
    - pip installations
    - editable installs

    Returns:
        Absolute path to respec-ai package root directory (src directory)

    Raises:
        PackageInfoError: If package path cannot be determined
    """
    try:
        src_init = Path(src.__file__).parent
        return src_init.resolve()

    except ImportError as e:
        raise PackageInfoError(
            f'Cannot import src module: {e}\nrespec-ai package may not be properly installed.'
        ) from e
    except Exception as e:
        raise PackageInfoError(f'Unexpected error determining package path: {e}') from e


def _is_git_dirty() -> bool:
    try:
        package_path = get_package_installation_path()
        repo_root = package_path.parent

        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )

        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        return False


def _get_git_commit() -> str | None:
    try:
        package_path = get_package_installation_path()
        repo_root = package_path.parent

        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_package_version() -> str:
    """Get installed package version using importlib.metadata.

    For local development with uncommitted changes, returns a dev version
    based on git state (e.g., "0.6.5-dev+a37bf78-dirty").

    Returns:
        Version string (e.g., "0.4.5" or "0.6.5-dev+a37bf78-dirty")

    Raises:
        PackageInfoError: If version cannot be determined
    """
    try:
        base_version = version('respec-ai')

        if _is_git_dirty():
            commit = _get_git_commit()
            if commit:
                return f'{base_version}-dev+{commit}-dirty'
            return f'{base_version}-dev-dirty'

        commit = _get_git_commit()
        if commit:
            result = subprocess.run(
                ['git', 'describe', '--exact-match', '--tags', 'HEAD'],
                cwd=get_package_installation_path().parent,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode != 0:
                return f'{base_version}-dev+{commit}'

        return base_version

    except PackageNotFoundError as e:
        raise PackageInfoError('respec-ai package not found. The package may not be properly installed.') from e
    except Exception as e:
        raise PackageInfoError(f'Error reading package version: {e}') from e
