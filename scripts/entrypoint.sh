#!/bin/bash
set -e

echo "=== Running database migrations (dev) ==="
uv run python scripts/migrate.py
echo "=== Dev migrations complete ==="

if DATABASE_URL="${DATABASE_URL%/*}/respec_test" uv run python scripts/migrate.py 2>/dev/null; then
    echo "=== Test database migrations complete ==="
else
    echo "=== Test database not available (skipping) ==="
fi

mkdir -p /app/logs && touch /app/logs/mcp-server.log
exec tail -F /app/logs/mcp-server.log
