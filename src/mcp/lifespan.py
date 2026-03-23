import logging
from collections.abc import AsyncIterator
from typing import Any

from fastmcp.server.lifespan import lifespan

from src.utils.database_pool import db_pool
from src.utils.setting_configs import mcp_settings
from src.utils.state_manager import InMemoryStateManager, PostgresStateManager, StateManager


logger = logging.getLogger(__name__)


@lifespan
async def mcp_lifespan(server: Any) -> AsyncIterator[dict[str, StateManager]]:
    manager_type = mcp_settings.state_manager

    logger.info(f'Initializing state manager: {manager_type}')

    pg_manager: PostgresStateManager | None = None

    if manager_type == 'database':
        pg_manager = PostgresStateManager()
        await pg_manager.initialize()
        logger.info('PostgresStateManager initialized with database connection')
        manager: StateManager = pg_manager
    else:
        manager = InMemoryStateManager()
        logger.info('InMemoryStateManager initialized')

    try:
        yield {'state_manager': manager}
    finally:
        if pg_manager is not None:
            await pg_manager.close()
            await db_pool.close()
            logger.info('Database connections closed')
