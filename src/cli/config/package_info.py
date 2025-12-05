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


def get_package_version() -> str:
    """Get installed package version using importlib.metadata.

    Returns:
        Version string (e.g., "0.4.5")

    Raises:
        PackageInfoError: If version cannot be determined
    """
    try:
        return version('respec-ai')
    except PackageNotFoundError as e:
        raise PackageInfoError('respec-ai package not found. The package may not be properly installed.') from e
    except Exception as e:
        raise PackageInfoError(f'Error reading package version: {e}') from e
