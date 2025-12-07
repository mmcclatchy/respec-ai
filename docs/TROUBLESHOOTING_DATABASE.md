# Database StateManager Troubleshooting Guide

## Common Errors and Solutions

### Connection Errors

#### Error: "Database pool not initialized. Call initialize() first."

**Cause**: Attempting to use `db_pool.acquire()` before calling `await db_pool.initialize()`.

**Solution**:
```python
from src.utils.database_pool import db_pool

# Initialize pool first
await db_pool.initialize()

# Then use acquire
async with db_pool.acquire() as conn:
    result = await conn.fetchval('SELECT 1')
```

#### Error: "could not connect to server: Connection refused"

**Cause**: PostgreSQL server not running or wrong host/port.

**Solution**:
```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432

# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql@16

# Start PostgreSQL (Docker)
docker-compose -f docker-compose.dev.yml up -d db

# Verify connection string
echo $DATABASE_URL
```

#### Error: "FATAL: password authentication failed for user"

**Cause**: Incorrect database credentials.

**Solution**:
1. Verify credentials in `DATABASE_URL` environment variable
2. Reset PostgreSQL user password:
   ```sql
   ALTER USER respec WITH PASSWORD 'new_password';
   ```
3. Update connection string:
   ```bash
   export DATABASE_URL=postgresql://respec:new_password@localhost:5432/respec_dev
   ```

#### Error: "FATAL: database 'respec_dev' does not exist"

**Cause**: Database not created.

**Solution**:
```bash
psql -U postgres -c "CREATE DATABASE respec_dev;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE respec_dev TO respec;"
```

### Pool Exhaustion Errors

#### Error: "asyncpg.exceptions.TooManyConnectionsError"

**Cause**: Connection pool exhausted (all connections in use).

**Symptoms**:
- Requests hang for `pool_timeout` seconds
- Error after timeout expires

**Solutions**:

1. **Increase pool size**:
   ```bash
   export DATABASE_POOL_MAX_SIZE=50
   ```

2. **Check for connection leaks**:
   ```python
   # Always use context manager
   async with db_pool.acquire() as conn:
       await conn.execute('SELECT 1')
   # Connection automatically returned here

   # Never do this (connection leak)
   conn = await db_pool.acquire()  # Connection never returned
   await conn.execute('SELECT 1')
   ```

3. **Monitor active connections**:
   ```sql
   SELECT count(*) as active_connections
   FROM pg_stat_activity
   WHERE datname = 'respec_dev' AND state = 'active';
   ```

#### Error: "timeout acquiring a connection from pool"

**Cause**: All connections busy, timeout reached.

**Solutions**:

1. **Increase timeout**:
   ```bash
   export DATABASE_POOL_TIMEOUT=60.0
   ```

2. **Optimize slow queries**:
   ```sql
   -- Find slow queries
   SELECT pid, now() - query_start as duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - query_start > interval '5 seconds'
   ORDER BY duration DESC;

   -- Kill slow query (if needed)
   SELECT pg_terminate_backend(pid);
   ```

### Migration Errors

#### Error: "relation 'loop_states' already exists"

**Cause**: Attempting to run migrations twice.

**Solutions**:

1. **Check migration history**:
   ```sql
   SELECT * FROM schema_migrations ORDER BY version;
   ```

2. **Drop and recreate** (DEVELOPMENT ONLY):
   ```bash
   psql -U respec -d respec_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   psql -U respec -d respec_dev -f migrations/001_initial_schema.sql
   psql -U respec -d respec_dev -f migrations/002_add_indexes.sql
   ```

3. **Use conditional migrations**:
   ```sql
   CREATE TABLE IF NOT EXISTS loop_states (...);
   ```

#### Error: "extension 'pg_trgm' does not exist"

**Cause**: PostgreSQL trigram extension not installed.

**Solution**:
```sql
-- Install extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

### Query Errors

#### Error: "UniqueViolationError: duplicate key value violates unique constraint"

**Cause**: Attempting to insert duplicate `(project_name, spec_name)` pair.

**Solution**:
Use `ON CONFLICT` for upsert operations:
```python
await conn.execute(
    '''
    INSERT INTO technical_specs (project_name, spec_name, ...)
    VALUES ($1, $2, ...)
    ON CONFLICT (project_name, spec_name) DO UPDATE SET
        architecture = $3,
        updated_at = CURRENT_TIMESTAMP
    ''',
    project_name, spec_name, architecture
)
```

#### Error: "CheckViolationError: new row violates check constraint"

**Cause**: Data violates table CHECK constraint.

**Examples**:
- `current_score` outside 0-100 range
- `iteration` less than 1
- Invalid `loop_type` or `status` value

**Solution**:
```python
# Validate data before insertion
assert 0 <= score <= 100, "Score must be between 0 and 100"
assert iteration >= 1, "Iteration must be >= 1"
assert loop_type in ['plan', 'roadmap', 'spec', 'build_plan', 'build_code', 'analyst']
```

#### Error: "asyncpg.exceptions.PostgresSyntaxError"

**Cause**: Invalid SQL syntax.

**Debugging**:
1. Log the SQL query before execution:
   ```python
   logger.debug(f"Executing: {query} with params: {params}")
   await conn.execute(query, *params)
   ```

2. Test query in `psql`:
   ```bash
   psql -U respec -d respec_dev
   # Paste and test query
   ```

### JSONB Errors

#### Error: "invalid input syntax for type json"

**Cause**: Malformed JSON data in JSONB field.

**Solution**:
```python
import json

# Validate JSON before insertion
feedback_json = json.dumps([fb.model_dump(mode='json') for fb in feedback_history])

# Or use Pydantic serialization
feedback_json = [fb.model_dump(mode='json') for fb in feedback_history]  # Returns valid dicts
```

#### Error: "CriticFeedback validation error" after retrieval

**Cause**: JSONB data doesn't match Pydantic schema.

**Debugging**:
```python
try:
    feedback_list = [CriticFeedback.model_validate(fb) for fb in row['feedback_history']]
except ValidationError as e:
    logger.error(f"Invalid feedback data: {row['feedback_history']}")
    logger.error(f"Validation error: {e}")
    raise
```

## Performance Issues

### Slow Queries

#### Symptom: Queries taking > 1 second

**Diagnosis**:
```sql
-- Enable query logging
ALTER DATABASE respec_dev SET log_min_duration_statement = 1000;  -- Log queries > 1s

-- Find slow queries
SELECT
  substring(query, 1, 50) as short_query,
  mean_exec_time,
  calls,
  total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Solutions**:

1. **Add missing indexes**:
   ```sql
   -- Check index usage
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
   FROM pg_stat_user_indexes
   WHERE schemaname = 'public'
   ORDER BY idx_scan ASC;

   -- Add index if needed
   CREATE INDEX idx_custom ON table_name(column_name);
   ```

2. **Use EXPLAIN ANALYZE**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM technical_specs WHERE project_name = 'my-project';
   ```
   Look for:
   - Sequential Scans (should use indexes instead)
   - High cost estimates
   - Actual time vs planned time discrepancies

3. **Optimize JSONB queries**:
   ```sql
   -- Slow (full JSONB scan)
   SELECT * FROM loop_states WHERE feedback_history::text LIKE '%score%';

   -- Fast (GIN index)
   SELECT * FROM loop_states WHERE feedback_history @> '[{"score": 90}]';
   ```

### High Memory Usage

#### Symptom: PostgreSQL consuming excessive RAM

**Diagnosis**:
```sql
-- Check cache hit ratio (should be > 95%)
SELECT
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit) as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;
```

**Solutions**:

1. **Tune shared_buffers** (PostgreSQL config):
   ```ini
   # postgresql.conf
   shared_buffers = 256MB  # 25% of RAM for dedicated server
   effective_cache_size = 1GB  # 50-75% of RAM
   ```

2. **Reduce connection pool size**:
   ```bash
   export DATABASE_POOL_MAX_SIZE=10
   ```

3. **Run VACUUM regularly**:
   ```bash
   psql -U respec -d respec_dev -c "VACUUM ANALYZE;"
   ```

### High CPU Usage

#### Symptom: PostgreSQL using > 80% CPU

**Diagnosis**:
```sql
-- Find expensive queries
SELECT pid, query, state, wait_event_type
FROM pg_stat_activity
WHERE state = 'active' AND pid <> pg_backend_pid()
ORDER BY query_start;
```

**Solutions**:

1. **Optimize query joins**:
   ```sql
   -- Before (slow)
   SELECT * FROM technical_specs
   WHERE project_name IN (SELECT project_name FROM roadmaps);

   -- After (fast)
   SELECT ts.* FROM technical_specs ts
   INNER JOIN roadmaps r ON ts.project_name = r.project_name;
   ```

2. **Limit result sets**:
   ```python
   # Avoid fetching entire table
   rows = await conn.fetch('SELECT * FROM technical_specs LIMIT 100')
   ```

3. **Use connection pooling**:
   - Reduces overhead of connection creation
   - Managed automatically by `db_pool`

## Connection Pool Tuning

### Sizing Guidelines

```python
# Calculate optimal pool size
concurrent_requests = 50  # Expected peak concurrent requests
buffer = 10  # Safety margin

min_pool_size = max(5, concurrent_requests // 4)
max_pool_size = concurrent_requests + buffer

# Set environment variables
export DATABASE_POOL_MIN_SIZE={min_pool_size}
export DATABASE_POOL_MAX_SIZE={max_pool_size}
```

### Monitoring Pool Health

```python
# Custom monitoring script
async def monitor_pool():
    from src.utils.database_pool import db_pool

    while True:
        async with db_pool.acquire() as conn:
            active = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = 'respec_dev'"
            )
            print(f"Active connections: {active}")

        await asyncio.sleep(60)
```

### Pool Configuration Recommendations

| Metric | Development | Staging | Production |
|--------|-------------|---------|------------|
| Min Size | 2 | 5 | 10 |
| Max Size | 10 | 20 | 50 |
| Timeout | 10s | 30s | 60s |
| Command Timeout | 30s | 60s | 120s |
| Max Inactive | 180s | 300s | 600s |

## Data Integrity Issues

### Orphaned Records

#### Symptom: Records without parent references

**Diagnosis**:
```sql
-- Find specs without projects
SELECT project_name FROM technical_specs
WHERE project_name NOT IN (SELECT project_name FROM roadmaps);

-- Find loop history without loops
SELECT loop_id FROM loop_history
WHERE loop_id NOT IN (SELECT id FROM loop_states);
```

**Solution**:
```sql
-- Cleanup orphaned records
DELETE FROM technical_specs
WHERE project_name NOT IN (SELECT project_name FROM roadmaps);

-- Should not happen due to CASCADE DELETE constraints
```

### Stale Data

#### Symptom: `updated_at` timestamps not updating

**Solution**:
```sql
-- Add trigger for automatic updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_specs_updated_at BEFORE UPDATE ON technical_specs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Docker-Specific Issues

### Volume Permissions

#### Error: "initdb: could not access directory"

**Solution**:
```bash
# Fix volume permissions
docker-compose -f docker-compose.dev.yml down -v
docker volume rm respec_dev_data
docker-compose -f docker-compose.dev.yml up -d
```

### Migration Not Running

#### Symptom: Migrations not applied automatically

**Diagnosis**:
```bash
# Check entrypoint logs
docker-compose -f docker-compose.dev.yml logs db | grep -i migration

# Verify volume mount
docker-compose -f docker-compose.dev.yml exec db ls /docker-entrypoint-initdb.d
```

**Solution**:
1. Migrations only run on first initialization
2. To rerun, delete volume and recreate:
   ```bash
   docker-compose -f docker-compose.dev.yml down -v
   docker-compose -f docker-compose.dev.yml up -d
   ```

## Production Checklist

### Pre-Deployment

- [ ] Run migrations on staging environment first
- [ ] Verify connection pooling parameters
- [ ] Enable SSL/TLS for database connections
- [ ] Set up database backups (automated)
- [ ] Configure monitoring and alerting
- [ ] Test connection failover
- [ ] Review slow query log
- [ ] Validate VACUUM/ANALYZE scheduled

### Monitoring

```bash
# Essential metrics to track
1. Connection pool utilization (target: < 80%)
2. Query latency (p95 < 100ms)
3. Cache hit ratio (target: > 95%)
4. Database size growth rate
5. Failed connection attempts
```

### Backup Strategy

```bash
# Daily full backup (cron example)
0 2 * * * pg_dump -U respec -d respec_prod -F c -f /backups/daily_$(date +\%A).dump

# Hourly incremental backup (requires WAL archiving)
0 * * * * pg_basebackup -U respec -D /backups/hourly_$(date +\%H) -Ft -z -Xs
```

## Getting Help

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('src.utils.database_pool').setLevel(logging.DEBUG)
logging.getLogger('src.utils.state_manager').setLevel(logging.DEBUG)
```

### Capture Query Logs

```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- View logs (macOS Homebrew)
tail -f /opt/homebrew/var/log/postgresql@16.log

-- View logs (Docker)
docker-compose -f docker-compose.dev.yml logs -f db
```

### Diagnostic Queries

```sql
-- Active queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active';

-- Lock conflicts
SELECT * FROM pg_locks WHERE NOT granted;

-- Table bloat
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```
