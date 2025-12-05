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
        Absolute path to respec-ai package root directory

    Raises:
        PackageInfoError: If package path cannot be determined
    """
    try:
        services_init = Path(src.__file__).parent
        package_root = services_init.parent

        if not (package_root / 'pyproject.toml').exists():
            raise PackageInfoError(
                'Cannot determine respec-ai installation path. '
                f'Expected pyproject.toml at: {package_root}\n'
                'This may indicate a corrupted installation.'
            )

        return package_root.resolve()

    except ImportError as e:
        raise PackageInfoError(
            f'Cannot import src module: {e}\nrespec-ai package may not be properly installed.'
        ) from e
    except Exception as e:
        raise PackageInfoError(f'Unexpected error determining package path: {e}') from e


def get_package_version() -> str:
    """Get installed package version.

    Returns:
        Version string (e.g., "0.2.0")

    Raises:
        PackageInfoError: If version cannot be determined
    """
    try:
        package_root = get_package_installation_path()
        pyproject_path = package_root / 'pyproject.toml'

        content = pyproject_path.read_text(encoding='utf-8')

        for line in content.splitlines():
            if line.strip().startswith('version ='):
                version = line.split('=')[1].strip().strip('"').strip("'")
                return version

        raise PackageInfoError('Version not found in pyproject.toml')

    except PackageInfoError:
        raise
    except Exception as e:
        raise PackageInfoError(f'Error reading package version: {e}') from e
