#!/bin/bash
set -e

echo "Setting up test database..."

docker-compose -f docker-compose.dev.yml up -d db
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Create test database first
echo "Creating respec_test database..."
docker exec respec-ai-db-dev psql -U respec -d postgres -c "CREATE DATABASE respec_test WITH OWNER = respec;" 2>/dev/null || echo "Database already exists"

# Apply migrations to test database
echo "Applying migrations to respec_test..."
docker exec respec-ai-db-dev bash -c 'for f in /docker-entrypoint-initdb.d/*.sql; do [ -e "$f" ] && echo "Applying $(basename $f)..." && psql -U respec -d respec_test -f "$f"; done'

echo ""
echo "Test database ready!"
echo "Run: uv run pytest"
