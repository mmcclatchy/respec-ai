import asyncio
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Generator, Literal
from urllib.parse import SplitResult, urlsplit, urlunsplit

import asyncpg
import pytest
from pytest_mock import MockerFixture

from src.mcp.tools.loop_tools import LoopTools
from src.utils.database_pool import db_pool
from src.utils.setting_configs import LoopConfig, database_settings
from src.utils.state_manager import InMemoryStateManager, PostgresStateManager


logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parent.parent

_TEST_TABLES = (
    'loop_states',
    'objective_feedback',
    'roadmaps',
    'phases',
    'plans',
    'loop_to_phase_mappings',
    'loop_to_task_mappings',
    'user_feedback_entries',
    'loop_analysis',
    'tasks',
    'review_sections',
)
_TRUNCATE_SQL = f'TRUNCATE {", ".join(_TEST_TABLES)} RESTART IDENTITY CASCADE'


@dataclass(frozen=True)
class PostgresTestContext:
    worker_id: str
    mode: Literal['database', 'schema']
    database_url: str
    database_name: str
    schema_name: str | None


def _quote_ident(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _sanitize_worker_id(worker_id: str) -> str:
    sanitized = re.sub(r'[^a-z0-9]+', '_', worker_id.lower()).strip('_')
    return sanitized or 'worker'


def _replace_database_name(database_url: str, database_name: str) -> str:
    parsed = urlsplit(database_url)
    return urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=f'/{database_name}',
            query=parsed.query,
            fragment=parsed.fragment,
        )
    )


def _extract_database_name(database_url: str) -> str:
    parsed = urlsplit(database_url)
    database_name = parsed.path.lstrip('/')
    if not database_name:
        raise ValueError(f'Invalid DATABASE_URL (missing database name): {database_url}')
    return database_name


def _run_async(coro: Awaitable[Any]) -> Any:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _run_migrations(database_url: str, migration_search_path: str | None = None) -> None:
    env = os.environ.copy()
    env['DATABASE_URL'] = database_url
    if migration_search_path:
        env['MIGRATION_SEARCH_PATH'] = migration_search_path
    else:
        env.pop('MIGRATION_SEARCH_PATH', None)

    subprocess.run(
        [sys.executable, str(ROOT_DIR / 'scripts' / 'migrate.py')],
        cwd=ROOT_DIR,
        check=True,
        env=env,
    )


async def _is_database_reachable(database_url: str) -> bool:
    try:
        conn = await asyncpg.connect(dsn=database_url, timeout=2.0)
    except Exception:
        return False
    await conn.close()
    return True


async def _reset_worker_database(base_database_url: str, worker_database_name: str) -> None:
    admin_database_url = _replace_database_name(base_database_url, 'postgres')
    conn = await asyncpg.connect(dsn=admin_database_url, timeout=5.0)
    try:
        await conn.execute(
            'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()',
            worker_database_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS {_quote_ident(worker_database_name)}')
        await conn.execute(f'CREATE DATABASE {_quote_ident(worker_database_name)}')
    finally:
        await conn.close()


async def _reset_worker_schema(base_database_url: str, schema_name: str) -> None:
    conn = await asyncpg.connect(dsn=base_database_url, timeout=5.0)
    try:
        await conn.execute(f'DROP SCHEMA IF EXISTS {_quote_ident(schema_name)} CASCADE')
        await conn.execute(f'CREATE SCHEMA {_quote_ident(schema_name)}')
    finally:
        await conn.close()


async def _cleanup_test_tables() -> None:
    async with db_pool.acquire() as conn:
        await conn.execute(_TRUNCATE_SQL)


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
def isolated_loop_tools(isolated_state_manager: InMemoryStateManager) -> LoopTools:
    return LoopTools(isolated_state_manager)


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
        phase_threshold=90,
        task_threshold=95,
        # Improvement thresholds for stagnation detection
        plan_improvement_threshold=5,
        analyst_improvement_threshold=10,
        roadmap_improvement_threshold=10,
        phase_improvement_threshold=5,
        task_improvement_threshold=5,
        # Checkpoint frequencies for user input triggers
        plan_checkpoint_frequency=5,
        analyst_checkpoint_frequency=3,
        roadmap_checkpoint_frequency=5,
        phase_checkpoint_frequency=5,
        task_checkpoint_frequency=5,
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
def postgres_test_context(worker_id: str) -> Generator[PostgresTestContext | None, None, None]:
    base_database_url = database_settings.url
    is_reachable = bool(_run_async(_is_database_reachable(base_database_url)))
    if not is_reachable:
        logger.warning('PostgreSQL not available at configured DATABASE_URL')
        yield None
        return

    worker_suffix = _sanitize_worker_id(worker_id)
    base_database_name = _extract_database_name(base_database_url)
    worker_database_name = f'{base_database_name}_{worker_suffix}'
    worker_schema_name = f'test_{worker_suffix}'

    context: PostgresTestContext | None = None

    if db_pool._pool is not None:
        _run_async(db_pool.close())

    try:
        _run_async(_reset_worker_database(base_database_url, worker_database_name))
        worker_database_url = _replace_database_name(base_database_url, worker_database_name)
        _run_migrations(worker_database_url)
        database_settings.url = worker_database_url
        database_settings.search_path = None
        context = PostgresTestContext(
            worker_id=worker_id,
            mode='database',
            database_url=worker_database_url,
            database_name=worker_database_name,
            schema_name=None,
        )
    except asyncpg.InsufficientPrivilegeError:
        _run_async(_reset_worker_schema(base_database_url, worker_schema_name))
        _run_migrations(base_database_url, migration_search_path=f'{worker_schema_name},public')
        database_settings.url = base_database_url
        database_settings.search_path = f'{worker_schema_name},public'
        context = PostgresTestContext(
            worker_id=worker_id,
            mode='schema',
            database_url=base_database_url,
            database_name=base_database_name,
            schema_name=worker_schema_name,
        )

    yield context

    if db_pool._pool is not None:
        _run_async(db_pool.close())

    if context is None:
        return

    if context.mode == 'database':
        _run_async(_reset_worker_database(base_database_url, context.database_name))
    elif context.schema_name:
        _run_async(_reset_worker_schema(base_database_url, context.schema_name))


@pytest.fixture(scope='session')
def check_database_available(postgres_test_context: PostgresTestContext | None) -> bool:
    return postgres_test_context is not None


@pytest.fixture(scope='function')
async def db_state_manager(
    postgres_test_context: PostgresTestContext | None,
) -> AsyncGenerator[PostgresStateManager, None]:
    if postgres_test_context is None:
        pytest.skip('PostgreSQL database not available. Start with: docker-compose -f docker-compose.dev.yml up -d')

    manager = PostgresStateManager(max_history_size=3)
    await manager.initialize()

    yield manager

    await _cleanup_test_tables()
    await db_pool.close()
