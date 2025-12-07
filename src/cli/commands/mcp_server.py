import subprocess
import sys
from argparse import ArgumentParser, Namespace

from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error


def add_arguments(parser: ArgumentParser) -> None:
    pass


def run(args: Namespace) -> int:
    try:
        manager = DockerManager()
        status = manager.get_container_status()

        if not status['running']:
            print_error('MCP server container is not running')
            print_error('Run: respec-ai docker start')
            return 1

        result = subprocess.run(
            ['docker', 'exec', '-i', status['name'], 'uv', 'run', 'respec-server'],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=False,
        )

        return result.returncode

    except DockerManagerError as e:
        print_error(f'Docker error: {e}')
        return 1
    except Exception as e:
        print_error(f'MCP server failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Start RespecAI MCP server')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
