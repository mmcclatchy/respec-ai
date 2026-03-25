import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import asyncpg


logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / 'migrations'


async def run() -> None:
    database_url = os.environ['DATABASE_URL']
    conn = await asyncpg.connect(database_url)
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
        await conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stdout)
    asyncio.run(run())
