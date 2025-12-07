# Database Migrations

## Running Migrations

### Development
```bash
psql -U respec -d respec_dev -f migrations/001_initial_schema.sql
psql -U respec -d respec_dev -f migrations/002_add_indexes.sql
```

### Docker Compose
Migrations auto-run on container startup via docker-entrypoint-initdb.d

## Creating New Migrations

1. Create file: `migrations/00X_description.sql`
2. Include tracking: `INSERT INTO schema_migrations (version, description) VALUES (X, 'description');`
