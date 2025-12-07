import logging
import os

from src.utils.state_manager import InMemoryStateManager, PostgresStateManager, StateManager


logger = logging.getLogger(__name__)


async def create_state_manager_async() -> StateManager:
    """Create state manager based on STATE_MANAGER environment variable (async version).

    Returns:
        StateManager: Configured state manager instance

    Environment Variables:
        STATE_MANAGER: 'memory' (default) or 'database'

    Raises:
        ValueError: If STATE_MANAGER contains unknown value
    """
    manager_type = os.getenv('STATE_MANAGER', 'memory').lower()

    logger.info(f'Initializing state manager: {manager_type}')

    if manager_type == 'memory':
        return InMemoryStateManager()
    elif manager_type == 'database':
        manager = PostgresStateManager()
        await manager.initialize()
        logger.info('PostgresStateManager initialized')
        return manager
    else:
        raise ValueError(f'Unknown STATE_MANAGER value: {manager_type}. Valid options: "memory", "database"')


def create_state_manager() -> StateManager:
    """Create state manager based on STATE_MANAGER environment variable (sync version).

    Returns:
        StateManager: Configured state manager instance

    Environment Variables:
        STATE_MANAGER: 'memory' (default) or 'database'

    Raises:
        ValueError: If STATE_MANAGER contains unknown value
        RuntimeError: If 'database' mode selected (requires async initialization)
    """
    manager_type = os.getenv('STATE_MANAGER', 'memory').lower()

    if manager_type == 'database':
        raise RuntimeError(
            'Database state manager requires async initialization. '
            'Use: await create_state_manager_async() in async contexts'
        )

    logger.info(f'Initializing state manager: {manager_type}')

    if manager_type == 'memory':
        return InMemoryStateManager()
    else:
        raise ValueError(f'Unknown STATE_MANAGER value: {manager_type}. Valid options: "memory", "database"')


# Global singleton (sync contexts only)
state_manager = create_state_manager()
