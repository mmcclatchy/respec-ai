from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
from docker.models.images import Image
from src.cli.config.package_info import get_package_version


class DockerManagerError(Exception):
    pass


class DockerManager:
    IMAGE_NAME = 'respec-ai-server'
    CONTAINER_NAME_PREFIX = 'respec-ai'
    DB_CONTAINER_NAME = 'respec-ai-db-prod'
    DB_NETWORK_NAME = 'respec-prod-network'
    DB_VOLUME_NAME = 'respec_prod_data'
    REGISTRIES = [
        'ghcr.io/mmcclatchy/respec-ai-server',
    ]

    def __init__(self) -> None:
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise DockerManagerError(f'Failed to connect to Docker daemon: {e}') from e

    def get_image_version(self) -> str:
        return get_package_version()

    def get_image_tag(self, version: str | None = None) -> str:
        version = version or self.get_image_version()
        return f'{self.IMAGE_NAME}:{version}'

    def get_container_name(self, version: str | None = None) -> str:
        version = version or self.get_image_version()
        return f'{self.CONTAINER_NAME_PREFIX}-{version}'

    def verify_image_exists(self, version: str | None = None) -> bool:
        image_tag = self.get_image_tag(version)
        try:
            self.client.images.get(image_tag)
            return True
        except ImageNotFound:
            return False

    def get_image(self, version: str | None = None) -> Image | None:
        image_tag = self.get_image_tag(version)
        try:
            return self.client.images.get(image_tag)
        except ImageNotFound:
            return None

    def pull_image(self, version: str | None = None) -> Image:
        version = version or self.get_image_version()
        image_tag = self.get_image_tag(version)

        for registry in self.REGISTRIES:
            full_tag = f'{registry}:{version}'
            try:
                print(f'Pulling from {registry}...')
                image: Image = self.client.images.pull(full_tag)
                # Tag as local name for consistency
                image.tag(self.IMAGE_NAME, version)
                print(f'✓ Successfully pulled {image_tag}')
                return image
            except DockerException as e:
                print(f'✗ Failed to pull from {registry}: {e}')
                continue

        raise DockerManagerError(
            f'Failed to pull {image_tag} from registry.\nTry building locally: respec-ai docker build'
        )

    def build_image(self, version: str | None = None, path: str | Path = '.') -> Image:
        version = version or self.get_image_version()
        image_tag = self.get_image_tag(version)

        try:
            print(f'Building {image_tag} from {path}...')
            image, logs = self.client.images.build(
                path=str(path),
                tag=image_tag,
                rm=True,
                forcerm=True,
            )

            # Print build logs
            for log in logs:
                if isinstance(log, dict) and 'stream' in log:
                    stream = log['stream']
                    if isinstance(stream, str):
                        print(stream.strip())

            print(f'✓ Successfully built {image_tag}')
            return image
        except DockerException as e:
            raise DockerManagerError(f'Failed to build image: {e}') from e

    def start_container(self, version: str | None = None, detach: bool = True) -> Container:
        version = version or self.get_image_version()
        image_tag = self.get_image_tag(version)
        container_name = self.get_container_name(version)

        # Check if container already exists
        existing = self.get_container(version)
        if existing:
            if existing.status == 'running':
                print(f'Container {container_name} is already running')
                return existing
            else:
                print(f'Starting existing container {container_name}...')
                existing.start()
                return existing

        # Verify image exists
        if not self.verify_image_exists(version):
            raise DockerManagerError(f'Image {image_tag} not found. Run: respec-ai docker pull')

        try:
            print(f'Creating container {container_name}...')
            container: Container = self.client.containers.run(  # type: ignore
                image=image_tag,
                name=container_name,
                detach=detach,
                remove=False,  # Don't auto-remove on stop
                restart_policy={'Name': 'unless-stopped'},
            )
            print(f'✓ Container {container_name} started')
            return container
        except DockerException as e:
            raise DockerManagerError(f'Failed to start container: {e}') from e

    def stop_container(self, version: str | None = None, timeout: int = 10) -> None:
        container_name = self.get_container_name(version)
        container = self.get_container(version)

        if not container:
            print(f'Container {container_name} not found')
            return

        if container.status != 'running':
            print(f'Container {container_name} is not running (status: {container.status})')
            return

        try:
            print(f'Stopping container {container_name}...')
            container.stop(timeout=timeout)
            print(f'✓ Container {container_name} stopped')
        except DockerException as e:
            raise DockerManagerError(f'Failed to stop container: {e}') from e

    def restart_container(self, version: str | None = None) -> Container:
        container_name = self.get_container_name(version)
        container = self.get_container(version)

        if not container:
            raise DockerManagerError(f'Container {container_name} not found')

        try:
            print(f'Restarting container {container_name}...')
            container.restart()
            print(f'✓ Container {container_name} restarted')
            return container
        except DockerException as e:
            raise DockerManagerError(f'Failed to restart container: {e}') from e

    def remove_container(self, version: str | None = None, force: bool = False) -> None:
        container_name = self.get_container_name(version)
        container = self.get_container(version)

        if not container:
            print(f'Container {container_name} not found')
            return

        try:
            print(f'Removing container {container_name}...')
            container.remove(force=force)
            print(f'✓ Container {container_name} removed')
        except DockerException as e:
            raise DockerManagerError(f'Failed to remove container: {e}') from e

    def get_container(self, version: str | None = None) -> Container | None:
        container_name = self.get_container_name(version)
        try:
            return self.client.containers.get(container_name)
        except NotFound:
            return None

    def get_container_status(self, version: str | None = None) -> dict[str, Any]:
        container_name = self.get_container_name(version)
        container = self.get_container(version)

        if not container:
            return {
                'exists': False,
                'running': False,
                'status': 'not found',
                'name': container_name,
            }

        container.reload()
        image_name = 'unknown'
        if container.image and hasattr(container.image, 'tags') and container.image.tags:
            image_name = container.image.tags[0]

        return {
            'exists': True,
            'running': container.status == 'running',
            'status': container.status,
            'name': container.name,
            'id': container.short_id,
            'image': image_name,
            'created': container.attrs.get('Created', 'unknown'),
        }

    def get_container_logs(self, version: str | None = None, lines: int = 100) -> str:
        container = self.get_container(version)

        if not container:
            return f'Container {self.get_container_name(version)} not found'

        try:
            logs = container.logs(tail=lines, timestamps=True)
            return logs.decode('utf-8')
        except DockerException as e:
            raise DockerManagerError(f'Failed to get container logs: {e}') from e

    def ensure_running(self, version: str | None = None) -> Container:
        status = self.get_container_status(version)

        if status['running']:
            container = self.get_container(version)
            if not container:
                raise DockerManagerError('Container reported running but not found')
            return container

        if status['exists']:
            return self.restart_container(version)

        return self.start_container(version)

    def list_all_containers(self) -> list[dict[str, Any]]:
        try:
            containers = self.client.containers.list(
                all=True,
                filters={'name': self.CONTAINER_NAME_PREFIX},
            )
            result = []
            for c in containers:
                image_name = 'unknown'
                if c.image and hasattr(c.image, 'tags') and c.image.tags:
                    image_name = c.image.tags[0]

                result.append(
                    {
                        'name': c.name,
                        'status': c.status,
                        'image': image_name,
                        'id': c.short_id,
                    }
                )
            return result
        except DockerException as e:
            raise DockerManagerError(f'Failed to list containers: {e}') from e

    def cleanup_old_versions(self) -> int:
        """Remove old respec-ai containers and images.

        Keeps only the current version matching the CLI.

        Returns:
            Number of items removed (containers + images)
        """
        current_version = self.get_image_version()
        current_container_name = self.get_container_name()
        current_image_tag = self.get_image_tag()
        removed_count = 0

        try:
            # Remove old containers
            containers = self.client.containers.list(
                all=True,
                filters={'name': self.CONTAINER_NAME_PREFIX},
            )
            for container in containers:
                if container.name != current_container_name:
                    print(f'Removing old container: {container.name}')
                    try:
                        container.remove(force=True)
                        removed_count += 1
                    except DockerException as e:
                        print(f'Warning: Failed to remove container {container.name}: {e}')

            # Remove old images
            images = self.client.images.list(name=self.IMAGE_NAME)
            for image in images:
                if not image.tags:
                    continue
                # Check if any tag matches current version
                is_current = any(tag == current_image_tag or tag == f'{self.IMAGE_NAME}:latest' for tag in image.tags)
                if not is_current:
                    for tag in image.tags:
                        if self.IMAGE_NAME in tag:
                            print(f'Removing old image: {tag}')
                            try:
                                self.client.images.remove(tag, force=True)
                                removed_count += 1
                            except DockerException as e:
                                print(f'Warning: Failed to remove image {tag}: {e}')
                            break

            # Also remove registry images (ghcr.io/...)
            for registry in self.REGISTRIES:
                images = self.client.images.list(name=registry)
                for image in images:
                    if not image.tags:
                        continue
                    is_current = any(
                        tag.endswith(f':{current_version}') or tag.endswith(':latest') for tag in image.tags
                    )
                    if not is_current:
                        for tag in image.tags:
                            if registry in tag:
                                print(f'Removing old image: {tag}')
                                try:
                                    self.client.images.remove(tag, force=True)
                                    removed_count += 1
                                except DockerException as e:
                                    print(f'Warning: Failed to remove image {tag}: {e}')
                                break

            return removed_count

        except DockerException as e:
            raise DockerManagerError(f'Failed to cleanup old versions: {e}') from e

    def cleanup_dangling_images(self) -> tuple[int, int]:
        try:
            result = self.client.images.prune(filters={'dangling': True})
            images_removed = len(result.get('ImagesDeleted', []) or [])
            space_reclaimed = result.get('SpaceReclaimed', 0)
            return (images_removed, space_reclaimed)
        except DockerException as e:
            raise DockerManagerError(f'Failed to cleanup dangling images: {e}') from e

    def get_database_container(self) -> Container | None:
        try:
            return self.client.containers.get(self.DB_CONTAINER_NAME)
        except NotFound:
            return None

    def stop_database_container(self, force: bool = False, timeout: int = 10) -> None:
        container = self.get_database_container()
        if not container:
            raise DockerManagerError(f'Database container {self.DB_CONTAINER_NAME} not found')

        try:
            if force:
                container.kill()
            else:
                container.stop(timeout=timeout)
        except DockerException as e:
            raise DockerManagerError(f'Failed to stop database container: {e}') from e

    def remove_database_container(self, force: bool = False) -> None:
        container = self.get_database_container()
        if not container:
            return

        try:
            container.remove(force=force)
        except DockerException as e:
            raise DockerManagerError(f'Failed to remove database container: {e}') from e

    def remove_image(self, version: str | None = None) -> None:
        image_tag = self.get_image_tag(version)
        try:
            self.client.images.remove(image_tag, force=True)
        except ImageNotFound:
            pass
        except DockerException as e:
            raise DockerManagerError(f'Failed to remove image: {e}') from e

    def remove_network(self) -> None:
        try:
            network = self.client.networks.get(self.DB_NETWORK_NAME)
            network.remove()
        except NotFound:
            pass
        except DockerException as e:
            raise DockerManagerError(f'Failed to remove network: {e}') from e

    def remove_volume(self) -> None:
        try:
            volume = self.client.volumes.get(self.DB_VOLUME_NAME)
            volume.remove()
        except NotFound:
            pass
        except DockerException as e:
            raise DockerManagerError(f'Failed to remove volume: {e}') from e

    def list_prod_containers(self) -> list[dict[str, Any]]:
        containers = []

        server = self.get_container()
        if server:
            image_name = 'unknown'
            if server.image and hasattr(server.image, 'tags') and server.image.tags:
                image_name = server.image.tags[0]
            containers.append(
                {
                    'name': server.name,
                    'running': server.status == 'running',
                    'image': image_name,
                    'created': server.attrs['Created'][:19].replace('T', ' '),
                }
            )

        db = self.get_database_container()
        if db:
            image_name = 'unknown'
            if db.image and hasattr(db.image, 'tags') and db.image.tags:
                image_name = db.image.tags[0]
            containers.append(
                {
                    'name': db.name,
                    'running': db.status == 'running',
                    'image': image_name,
                    'created': db.attrs['Created'][:19].replace('T', ' '),
                }
            )

        return containers
