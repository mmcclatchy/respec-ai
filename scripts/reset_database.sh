#!/bin/bash
set -e

# Database configuration
DB_USER="${DB_USER:-respec}"
DB_NAME="${DB_NAME:-respec_dev}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "🗑️  Dropping database $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

echo "📦 Creating database $DB_NAME..."
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "🔄 Running migrations..."
for migration in migrations/*.sql; do
    if [[ "$migration" == *"000_init_test_db.sql"* ]]; then
        echo "  ⏭️  Skipping test init: $migration"
        continue
    fi
    echo "  ✓ Applying: $migration"
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$migration" -q
done

echo "✅ Database reset complete!"
