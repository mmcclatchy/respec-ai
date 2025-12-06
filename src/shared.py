import logging
import os

from src.utils.state_manager import DatabaseStateManager, InMemoryStateManager, StateManager


logger = logging.getLogger(__name__)


def create_state_manager() -> StateManager:
    """Create state manager based on STATE_MANAGER environment variable.

    Returns:
        StateManager: Configured state manager instance

    Environment Variables:
        STATE_MANAGER: 'memory' (default) or 'database'

    Raises:
        ValueError: If STATE_MANAGER contains unknown value
        NotImplementedError: If 'database' selected (not yet implemented)
    """
    manager_type = os.getenv('STATE_MANAGER', 'memory').lower()

    logger.info(f'Initializing state manager: {manager_type}')

    if manager_type == 'memory':
        return InMemoryStateManager()
    elif manager_type == 'database':
        # This will raise NotImplementedError until database implementation ready
        return DatabaseStateManager()
    else:
        raise ValueError(f'Unknown STATE_MANAGER value: {manager_type}. Valid options: "memory", "database"')


# Global singleton
state_manager = create_state_manager()
