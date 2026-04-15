import pytest

from src.utils.database_pool import db_pool
from src.utils.state_manager import PostgresStateManager


@pytest.mark.asyncio
async def test_postgres_context_uses_worker_isolated_storage(
    db_state_manager: PostgresStateManager,
    postgres_test_context: object,
    worker_id: str,
) -> None:
    assert db_state_manager is not None
    assert postgres_test_context is not None

    context = postgres_test_context
    assert getattr(context, 'worker_id') == worker_id

    async with db_pool.acquire() as conn:
        current_database = await conn.fetchval('SELECT current_database()')
        current_schema = await conn.fetchval('SELECT current_schema()')

    if getattr(context, 'mode') == 'database':
        assert current_database == getattr(context, 'database_name')
    else:
        assert current_schema == getattr(context, 'schema_name')
