import asyncio
import logging
from typing import AsyncGenerator, Generator

import pytest
from pytest_mock import MockerFixture

from src.mcp.tools.loop_tools import LoopTools
from src.mcp.tools.roadmap_tools import RoadmapTools
from src.utils.setting_configs import LoopConfig
from src.utils.state_manager import InMemoryStateManager, PostgresStateManager


import os
import asyncpg
from src.utils.database_pool import db_pool


def pytest_configure(config: pytest.Config) -> None:
    logging.getLogger('state_manager').setLevel(logging.WARNING)
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('mcp').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.WARNING)
    config.addinivalue_line('markers', 'database: mark test as requiring PostgreSQL database')


# No longer need to mock the entire MCP server module since we removed fake markdown tools


@pytest.fixture
def isolated_state_manager() -> InMemoryStateManager:
    return InMemoryStateManager()


@pytest.fixture
def isolated_roadmap_tools(isolated_state_manager: InMemoryStateManager) -> RoadmapTools:
    return RoadmapTools(isolated_state_manager)


@pytest.fixture
def isolated_loop_tools(isolated_state_manager: InMemoryStateManager) -> LoopTools:
    return LoopTools(isolated_state_manager)


@pytest.fixture(autouse=True)
def mock_shared_state(
    mocker: MockerFixture, isolated_state_manager: InMemoryStateManager
) -> Generator[InMemoryStateManager, None, None]:
    mocker.patch('src.shared.state_manager', isolated_state_manager)
    mocker.patch('src.mcp.tools.roadmap_tools.state_manager', isolated_state_manager)
    mocker.patch('src.mcp.tools.loop_tools.state_manager', isolated_state_manager)
    yield isolated_state_manager


@pytest.fixture(autouse=True)
def stable_loop_config(mocker: MockerFixture) -> Generator[LoopConfig, None, None]:
    """Provide consistent loop configuration for all tests.

    This fixture ensures tests use known, stable threshold values regardless of
    environment variables or default changes.
    """
    test_config = LoopConfig(
        # Thresholds for loop completion
        plan_threshold=90,
        analyst_threshold=90,
        roadmap_threshold=90,
        spec_threshold=90,
        build_plan_threshold=90,
        build_code_threshold=95,
        # Improvement thresholds for stagnation detection
        plan_improvement_threshold=5,
        analyst_improvement_threshold=10,
        roadmap_improvement_threshold=10,
        spec_improvement_threshold=5,
        build_plan_improvement_threshold=5,
        build_code_improvement_threshold=5,
        # Checkpoint frequencies for user input triggers
        plan_checkpoint_frequency=5,
        analyst_checkpoint_frequency=3,
        roadmap_checkpoint_frequency=5,
        spec_checkpoint_frequency=5,
        build_plan_checkpoint_frequency=5,
        build_code_checkpoint_frequency=5,
    )

    mocker.patch('src.utils.setting_configs.loop_config', test_config)
    mocker.patch('src.utils.enums.loop_config', test_config)
    yield test_config


@pytest.fixture(scope='session')
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def check_database_available() -> bool:
    async def check_db() -> bool:
        try:
            conn = await asyncpg.connect(
                dsn=os.getenv('DATABASE_URL', 'postgresql://respec:respec@localhost:5433/respec_dev'),
                timeout=2.0,
            )
            await conn.close()
            return True
        except Exception:
            return False

    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        result = loop.run_until_complete(check_db())
    finally:
        loop.close()

    return result


@pytest.fixture(scope='function')
async def db_state_manager(check_database_available: bool) -> AsyncGenerator[PostgresStateManager, None]:
    if not check_database_available:
        pytest.skip('PostgreSQL database not available. Start with: docker-compose -f docker-compose.dev.yml up -d')

    manager = PostgresStateManager(max_history_size=3)
    await manager.initialize()

    yield manager

    async with db_pool.acquire() as conn:
        await conn.execute(
            'TRUNCATE loop_states, loop_history, objective_feedback, roadmaps, technical_specs, project_plans, loop_to_spec_mappings CASCADE'
        )

    await manager.close()
