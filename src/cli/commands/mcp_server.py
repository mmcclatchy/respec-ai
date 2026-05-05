import sys
from argparse import ArgumentParser, Namespace
from contextlib import redirect_stdout

from fastmcp.server import create_proxy

from src.cli.docker.manager import DockerManager, DockerManagerError


def add_arguments(parser: ArgumentParser) -> None:
    pass


def _stderr(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _find_running_server_container_name(manager: DockerManager) -> str | None:
    containers = manager.list_all_containers()

    name_fallback: str | None = None
    prefix = f'{manager.CONTAINER_NAME_PREFIX}-'
    for container in containers:
        name = str(container.get('name', ''))
        status = str(container.get('status', ''))
        image = str(container.get('image', ''))

        if name == manager.DB_CONTAINER_NAME:
            continue
        if not name.startswith(prefix):
            continue
        if status != 'running':
            continue

        # Strong signal: known respec server image naming.
        if manager.IMAGE_NAME in image or any(registry in image for registry in manager.REGISTRIES):
            return name

        # We still keep a name-only fallback for untagged images.
        name_fallback = name

    return name_fallback


def _backend_url(manager: DockerManager) -> str:
    return f'http://{manager.MCP_DAEMON_HOST}:{manager.MCP_DAEMON_PORT}{manager.MCP_DAEMON_PATH}'


def run(args: Namespace) -> int:
    try:
        manager = DockerManager()
        status = manager.get_container_status()

        target_container_name = status['name'] if status.get('running') else None

        if target_container_name is None:
            target_container_name = _find_running_server_container_name(manager)

        if target_container_name is None:
            # Start container as a last resort. Redirect manager prints away from stdout
            # so MCP stdio protocol remains clean.
            with redirect_stdout(sys.stderr):
                container = manager.ensure_running()
            target_container_name = container.name

        if target_container_name is None:
            raise DockerManagerError('Failed to resolve MCP server container')

        proxy = create_proxy(_backend_url(manager), name='respec-ai')
        proxy.run(transport='stdio', show_banner=False)
        return 0

    except DockerManagerError as e:
        _stderr(f'Docker error: {e}')
        return 1
    except Exception as e:
        _stderr(f'MCP server failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Start respec-ai MCP server')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
