import re
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.package_info import get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error, print_info, print_success, print_warning


GITHUB_REPO_URL = 'git+https://github.com/mmcclatchy/respec-ai.git'


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--skip-docker',
        action='store_true',
        help='Skip Docker image update',
    )


def _get_installed_version() -> str | None:
    result = subprocess.run(['uv', 'tool', 'list'], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    match = re.search(r'respec-ai\s+v([0-9]+\.[0-9]+\.[0-9]+)', result.stdout)
    return match.group(1) if match else None


def _update_docker(old_version: str, new_version: str) -> bool:
    try:
        docker_manager = DockerManager()
    except DockerManagerError as e:
        print_warning(f'Docker not available: {e}')
        print_info('Skip Docker update with: respec-ai update --skip-docker')
        return False

    is_same_version = old_version == new_version
    was_running = False

    if not is_same_version:
        old_status = docker_manager.get_container_status(version=old_version)
        was_running = old_status.get('running', False)

        if was_running:
            print_info('Stopping container...')
            docker_manager.stop_container(version=old_version)

    print_info(f'Pulling Docker image v{new_version}...')
    try:
        docker_manager.pull_image(version=new_version)
        print_success('Docker image updated')
    except DockerManagerError:
        print_warning(f'Docker image v{new_version} not yet available on registry')
        print_info('The GitHub Actions build may still be in progress')
        print_info('To pull manually once ready: respec-ai docker pull')

        if was_running:
            print_info('Restarting previous container...')
            try:
                docker_manager.ensure_running(version=old_version)
                print_success('Previous container restored')
            except DockerManagerError:
                print_warning('Could not restart previous container')
                print_info('Start manually when image is ready: respec-ai docker start')
        return False

    print_info('Starting container...')
    try:
        docker_manager.ensure_running(version=new_version)
        print_success('Container running')
    except DockerManagerError as e:
        print_warning(f'Failed to start container: {e}')
        if not is_same_version and was_running:
            print_info('Restarting previous container...')
            try:
                docker_manager.ensure_running(version=old_version)
                print_success('Previous container restored')
            except DockerManagerError:
                print_warning('Could not restart previous container')
        print_info('Start manually: respec-ai docker start')
        return False

    docker_manager.cleanup_old_versions(version=new_version)

    if is_same_version:
        print_info('No new CLI version found; refreshed Docker image and ensured container is running')

    return True


def run(args: Namespace) -> int:
    try:
        current_version = get_package_version()
        print_info(f'Current version: {current_version}')
        print_info('Checking for updates...')

        result = subprocess.run(
            ['uv', 'tool', 'install', '--force', GITHUB_REPO_URL],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print_error('Failed to update CLI package')
            print_error(result.stderr)
            return 1

        new_version = _get_installed_version() or get_package_version()

        if new_version == current_version:
            print_info(f'Already on latest version: {current_version}')
        else:
            print_success(f'Updated CLI: {current_version} → {new_version}')

        if not args.skip_docker:
            docker_updated = _update_docker(old_version=current_version, new_version=new_version)

            if docker_updated:
                reg_result = subprocess.run(
                    ['respec-ai', 'register-mcp', '--force'],
                    capture_output=True,
                    text=True,
                )
                if reg_result.returncode == 0:
                    print_success('MCP server re-registered')
                else:
                    print_warning('MCP re-registration skipped — run `respec-ai register-mcp --force`')

        config_path = Path.cwd() / '.respec-ai' / 'config.json'
        if config_path.exists():
            standards_dir = Path.cwd() / '.respec-ai' / 'config'
            standards_valid = True
            if standards_dir.exists():
                standards_validate = subprocess.run(
                    ['respec-ai', 'standards', 'validate'],
                    capture_output=True,
                    text=True,
                )
                if standards_validate.returncode != 0:
                    standards_valid = False
                    print_warning('Standards config validation failed — skipping standards render')
                    print_warning('Fix standards config and run: respec-ai standards validate')
                else:
                    subprocess.run(
                        ['respec-ai', 'standards', 'render'],
                        capture_output=True,
                        text=True,
                    )

            if standards_valid:
                regen_result = subprocess.run(
                    ['respec-ai', 'regenerate'],
                    capture_output=True,
                    text=True,
                )
                if regen_result.returncode == 0:
                    print_success('Templates regenerated')
                else:
                    print_warning('Template regeneration skipped — run `respec-ai regenerate` in your project')
            else:
                print_warning('Template regeneration skipped — fix standards config and run `respec-ai regenerate`')
        elif new_version != current_version:
            print_info('Run: respec-ai regenerate in your project directory to update templates')

        print_success('Update complete!')
        if new_version != current_version:
            print_info(f'New version: {new_version}')

        return 0

    except Exception as e:
        print_error(f'Update failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Update respec-ai to latest version')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
