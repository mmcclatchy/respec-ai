#!/bin/bash
set -e
uv run python scripts/migrate.py
mkdir -p /app/logs && touch /app/logs/mcp-server.log
exec tail -F /app/logs/mcp-server.log
