import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import asyncpg


logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / 'migrations'
_MIGRATION_LOCK_KEY = 7274938  # stable advisory lock key for migration serialization


async def _connect_with_retry(database_url: str, attempts: int = 30) -> asyncpg.Connection:
    for i in range(attempts):
        try:
            return await asyncpg.connect(database_url)
        except (asyncpg.CannotConnectNowError, ConnectionRefusedError):
            if i == attempts - 1:
                raise
            logger.info(f'Database not ready, retrying ({i + 1}/{attempts})...')
            await asyncio.sleep(2)
    raise RuntimeError('Unreachable')


async def run() -> None:
    database_url = os.environ['DATABASE_URL']
    conn = await _connect_with_retry(database_url)
    try:
        await conn.execute('SELECT pg_advisory_lock($1)', _MIGRATION_LOCK_KEY)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            rows = await conn.fetch('SELECT version FROM schema_migrations')
            applied = {row['version'] for row in rows}
            max_applied = max(applied, default=0)

            sql_files = sorted(
                f for f in MIGRATIONS_DIR.glob('*.sql') if re.match(r'^\d{3}_', f.name) and not f.name.startswith('000')
            )

            for sql_file in sql_files:
                version = int(sql_file.name[:3])

                if version in applied:
                    continue

                if version <= max_applied:
                    await conn.execute(
                        'INSERT INTO schema_migrations (version, description) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                        version,
                        sql_file.stem,
                    )
                    logger.info(f'Bootstrapped {sql_file.name} (applied before runner tracking)')
                    continue

                logger.info(f'Applying {sql_file.name}')
                sql = sql_file.read_text()
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        'INSERT INTO schema_migrations (version, description) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                        version,
                        sql_file.stem,
                    )
                logger.info(f'Applied {sql_file.name}')

            logger.info('Migrations complete')
        finally:
            await conn.execute('SELECT pg_advisory_unlock($1)', _MIGRATION_LOCK_KEY)
    finally:
        await conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stdout)
    asyncio.run(run())
