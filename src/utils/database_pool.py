import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from src.utils.setting_configs import database_settings


logger = logging.getLogger(__name__)


class DatabasePool:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        if self._pool is not None:
            return

        logger.info(f'Initializing database pool: {database_settings.url.split("@")[1]}')

        self._pool = await asyncpg.create_pool(
            dsn=database_settings.url,
            min_size=database_settings.pool_min_size,
            max_size=database_settings.pool_max_size,
            timeout=database_settings.pool_timeout,
            command_timeout=database_settings.command_timeout,
            max_inactive_connection_lifetime=database_settings.max_inactive_connection_lifetime,
        )

        logger.info('Database pool initialized')

    async def close(self) -> None:
        if self._pool is None:
            return

        logger.info('Closing database pool')
        await self._pool.close()
        self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        if self._pool is None:
            raise RuntimeError('Database pool not initialized. Call initialize() first.')

        async with self._pool.acquire() as conn:
            yield conn


db_pool = DatabasePool()
