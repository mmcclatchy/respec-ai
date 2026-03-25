#!/bin/bash
set -e
uv run python scripts/migrate.py
exec "$@"
