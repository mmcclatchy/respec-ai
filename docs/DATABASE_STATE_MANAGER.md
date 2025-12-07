# PostgresStateManager User Guide

## Overview

The PostgresStateManager provides persistent state storage using PostgreSQL 16, replacing the in-memory state manager for production deployments. All state data survives server restarts and supports concurrent access patterns.

## Quick Start

### Local Development with Docker Compose

```bash
# Start PostgreSQL and MCP server
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Check logs
docker-compose -f docker-compose.dev.yml logs -f mcp-server
```

Migrations run automatically on first startup via Docker entrypoint.

### Manual Setup (Without Docker)

1. **Start PostgreSQL**:
   ```bash
   psql -U postgres -c "CREATE DATABASE respec_dev;"
   psql -U postgres -c "CREATE USER respec WITH PASSWORD 'respec';"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE respec_dev TO respec;"
   ```

2. **Run Migrations**:
   ```bash
   psql -U respec -d respec_dev -f migrations/001_initial_schema.sql
   psql -U respec -d respec_dev -f migrations/002_add_indexes.sql
   ```

3. **Set Environment Variables**:
   ```bash
   export STATE_MANAGER=database
   export DATABASE_URL=postgresql://respec:respec@localhost:5432/respec_dev
   ```

4. **Start MCP Server**:
   ```bash
   uv run respec-server
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STATE_MANAGER` | `memory` | State manager type: `memory` or `database` |
| `DATABASE_URL` | `postgresql://respec:respec@localhost:5432/respec_dev` | PostgreSQL connection string |
| `DATABASE_POOL_MIN_SIZE` | `5` | Minimum connection pool size (1-50) |
| `DATABASE_POOL_MAX_SIZE` | `20` | Maximum connection pool size (1-100) |
| `DATABASE_POOL_TIMEOUT` | `30.0` | Pool acquisition timeout in seconds (1-120) |
| `DATABASE_COMMAND_TIMEOUT` | `60.0` | Query execution timeout in seconds (1-300) |
| `DATABASE_MAX_INACTIVE_CONNECTION_LIFETIME` | `300.0` | Max connection idle time in seconds (60+) |

### Connection String Format

```text
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Examples**:
- Local: `postgresql://respec:respec@localhost:5432/respec_dev`
- Docker: `postgresql://respec:respec@db:5432/respec_dev`
- Remote: `postgresql://user:pass@db.example.com:5432/respec_prod`

### Pool Sizing Guidelines

| Deployment | Min Size | Max Size | Reasoning |
|------------|----------|----------|-----------|
| Development | 2 | 10 | Low concurrency, fast startup |
| Staging | 5 | 20 | Moderate load testing |
| Production (< 100 users) | 10 | 50 | Handle traffic spikes |
| Production (> 100 users) | 20 | 100 | High concurrency |

**Formula**: `max_pool_size = (expected_concurrent_requests * 2) + buffer`

## Schema Overview

### Core Tables

#### loop_states
Stores active refinement loops with JSONB feedback history.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(8) | Unique loop identifier (primary key) |
| project_name | VARCHAR(255) | Associated project |
| loop_type | VARCHAR(50) | Loop category (plan, spec, build_plan, etc.) |
| status | VARCHAR(50) | Current status (initialized, in_progress, completed, user_input, refine) |
| current_score | INTEGER | Latest quality score (0-100) |
| score_history | INTEGER[] | Historical scores array |
| iteration | INTEGER | Current iteration number (>= 1) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last modification timestamp |
| feedback_history | JSONB | Array of CriticFeedback objects |

#### technical_specs
Stores technical specifications with frozen core fields.

**Frozen Fields** (immutable after iteration 0):
- `objectives`
- `scope`
- `dependencies`
- `deliverables`

**Flexible Fields** (can be updated):
- `architecture`
- `technology_stack`
- `functional_requirements`
- `non_functional_requirements`
- `development_plan`
- `testing_strategy`
- `research_requirements`
- `success_criteria`
- `integration_context`
- `additional_sections` (JSONB)

#### roadmaps
Project roadmap metadata with 16 required fields.

#### project_plans
Comprehensive project plans with 31 structured fields.

#### loop_history
Bounded queue tracking active loops (max 10 entries by default).

**Automatic Cleanup**: Oldest entries dropped when limit exceeded via `_enforce_loop_history_limit()`.

#### objective_feedback
Temporary feedback storage linked to loop states.

**CASCADE DELETE**: Automatically removed when parent loop deleted.

#### loop_to_spec_mappings
Temporary associations between refinement loops and specs.

**CASCADE DELETE**: Cleaned up when loop or spec deleted.

### Indexes

| Index | Type | Purpose |
|-------|------|---------|
| `idx_loop_states_project` | B-tree | Fast project-based loop lookups |
| `idx_loop_states_status` | B-tree | Filter loops by status |
| `idx_loop_states_created` | B-tree (DESC) | Chronological ordering |
| `idx_loop_history_sequence` | B-tree (DESC) | Bounded queue operations |
| `idx_specs_project` | B-tree | Project-based spec queries |
| `idx_specs_status` | B-tree | Filter specs by status |
| `idx_specs_iteration` | B-tree (DESC) | Version tracking |
| `idx_specs_name_search` | GIN (pg_trgm) | Fuzzy spec name matching |
| `idx_plans_status` | B-tree | Project plan filtering |

## Database Operations

### Backup and Restore

#### Full Database Backup
```bash
pg_dump -U respec -d respec_dev -F c -f backup_$(date +%Y%m%d_%H%M%S).dump
```

#### Restore from Backup
```bash
pg_restore -U respec -d respec_dev -c backup_20241206_120000.dump
```

#### Schema-Only Backup
```bash
pg_dump -U respec -d respec_dev --schema-only -f schema_backup.sql
```

#### Data-Only Backup
```bash
pg_dump -U respec -d respec_dev --data-only -f data_backup.sql
```

### Monitoring

#### Check Active Connections
```sql
SELECT datname, usename, state, query
FROM pg_stat_activity
WHERE datname = 'respec_dev';
```

#### Pool Usage Stats
```sql
SELECT
  numbackends as active_connections,
  xact_commit as transactions_committed,
  xact_rollback as transactions_rolled_back,
  blks_read as disk_blocks_read,
  blks_hit as cache_blocks_hit
FROM pg_stat_database
WHERE datname = 'respec_dev';
```

#### Table Sizes
```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Maintenance

#### Vacuum and Analyze
```bash
# Vacuum all tables (reclaim space)
psql -U respec -d respec_dev -c "VACUUM ANALYZE;"

# Aggressive vacuum (requires exclusive lock)
psql -U respec -d respec_dev -c "VACUUM FULL ANALYZE;"
```

#### Reindex
```bash
# Reindex specific table
psql -U respec -d respec_dev -c "REINDEX TABLE technical_specs;"

# Reindex entire database
psql -U respec -d respec_dev -c "REINDEX DATABASE respec_dev;"
```

## Performance Optimization

### Query Performance

1. **Use Indexes**: Queries should use indexed columns (`project_name`, `spec_status`, etc.)
2. **EXPLAIN ANALYZE**: Investigate slow queries
   ```sql
   EXPLAIN ANALYZE SELECT * FROM technical_specs WHERE project_name = 'my-project';
   ```
3. **Connection Pooling**: Reuse connections via `db_pool.acquire()`

### JSONB Query Optimization

```sql
-- Efficient JSONB queries
SELECT * FROM loop_states WHERE feedback_history @> '[{"score": 90}]';

-- Use GIN index for JSONB (if needed in future migrations)
CREATE INDEX idx_feedback_gin ON loop_states USING gin(feedback_history);
```

### Bounded Queue Performance

The loop history bounded queue uses `sequence_number` ordering for fast cleanup:

```sql
DELETE FROM loop_history
WHERE sequence_number IN (
    SELECT sequence_number FROM loop_history
    ORDER BY sequence_number DESC
    OFFSET 10
);
```

This operation is O(1) due to `idx_loop_history_sequence` index.

## Migration Management

### Adding New Migrations

1. Create migration file: `migrations/00X_description.sql`
2. Include tracking statement:
   ```sql
   INSERT INTO schema_migrations (version, description)
   VALUES (X, 'Description of changes');
   ```
3. Test locally before deploying:
   ```bash
   psql -U respec -d respec_test -f migrations/00X_description.sql
   ```

### Migration History

```sql
SELECT version, description, applied_at
FROM schema_migrations
ORDER BY version;
```

## Architecture Notes

### Why Raw SQL + Pydantic?

- **Simplicity**: No ORM overhead, explicit queries
- **Type Safety**: Pydantic validation at boundaries
- **Performance**: Direct database access
- **Debugging**: SQL queries visible in logs

### Async/Await Pattern

All PostgresStateManager methods are async:

```python
# Correct usage
manager = PostgresStateManager()
await manager.initialize()
spec = await manager.get_spec('project', 'spec-name')

# Incorrect (raises error)
spec = manager.get_spec('project', 'spec-name')  # Missing await
```

### Connection Lifecycle

1. **Startup**: `await db_pool.initialize()` creates pool
2. **Request**: `async with db_pool.acquire() as conn:` borrows connection
3. **Query**: `await conn.execute(...)` runs SQL
4. **Release**: Context manager returns connection to pool
5. **Shutdown**: `await db_pool.close()` terminates connections

## Comparison: Memory vs Database

| Feature | InMemoryStateManager | PostgresStateManager |
|---------|---------------------|---------------------|
| Persistence | ❌ Lost on restart | ✅ Survives restarts |
| Startup Time | < 1ms | ~100ms (pool init) |
| Concurrency | Single process | Multi-process safe |
| Backup/Restore | ❌ Not available | ✅ pg_dump/restore |
| Debugging | In-process state | SQL query logs |
| Best For | Development, testing | Staging, production |

## Troubleshooting

See [TROUBLESHOOTING_DATABASE.md](./TROUBLESHOOTING_DATABASE.md) for common issues and solutions.

## Security Considerations

### Connection Security

- **Production**: Use SSL/TLS connections (`sslmode=require`)
  ```text
  postgresql://user:pass@host:5432/db?sslmode=require
  ```
- **Passwords**: Store in environment variables, not code
- **Network**: Restrict PostgreSQL access via firewall rules

### SQL Injection Protection

All queries use parameterized placeholders (`$1`, `$2`):

```python
# Safe (parameterized)
await conn.execute('SELECT * FROM specs WHERE name = $1', spec_name)

# Unsafe (never do this)
await conn.execute(f'SELECT * FROM specs WHERE name = {spec_name}')
```

## Future Enhancements

- **Read Replicas**: Scale read operations
- **Partitioning**: Split large tables by project_name
- **Caching**: Redis layer for hot data
- **Audit Logs**: Track all state changes
