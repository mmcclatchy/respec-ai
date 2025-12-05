from src.cli.config.package_info import get_package_version


class VersionError(Exception):
    pass


def get_cli_version() -> str:
    """Get CLI package version.

    Returns:
        Version string (e.g., '0.3.0')

    Raises:
        VersionError: If version cannot be determined
    """
    try:
        return get_package_version()
    except Exception as e:
        raise VersionError(f'Failed to get CLI version: {e}') from e


def get_docker_image_tag(version: str | None = None) -> str:
    """Get full Docker image tag (name:version).

    Args:
        version: Specific version, or None for CLI version

    Returns:
        Image tag (e.g., 'respec-ai-server:0.3.0')
    """
    version = version or get_cli_version()
    return f'respec-ai-server:{version}'


def get_container_name(version: str | None = None) -> str:
    """Get Docker container name for version.

    Args:
        version: Specific version, or None for CLI version

    Returns:
        Container name (e.g., 'respec-ai-0.3.0')
    """
    version = version or get_cli_version()
    return f'respec-ai-{version}'


def validate_version_compatibility(cli_version: str, container_version: str) -> bool:
    """Validate CLI and container versions are compatible.

    Args:
        cli_version: CLI package version
        container_version: Docker container version

    Returns:
        True if compatible, False otherwise
    """
    return cli_version == container_version


def get_required_image_version() -> str:
    """Get required Docker image version for current CLI.

    Returns:
        Required image version (matches CLI version)
    """
    return get_cli_version()
