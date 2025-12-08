# Docker Deployment Guide

## Overview

respec-ai provides two distinct Docker deployment configurations:

- **Development**: For contributors working on the codebase
- **Production**: For end users installing via PyPI or Homebrew

These configurations are completely separate with no crossover.

## Development Deployment

### Purpose

Local development environment for contributors cloning the repository.

### Key Features

- Image: `respec-ai-dev:latest` (local only, never pushed to registry)
- Container: `respec-ai-mcp-dev`
- Database: `respec-ai-db-dev` (exposed on port 5433 for debugging)
- Network: `respec-dev-network`
- Source code mounted as volumes for live reloading
- Debug logging enabled

### Setup

```bash
# Clone repository
git clone https://github.com/mmcclatchy/respec-ai.git
cd respec-ai

# Build and start development environment
docker compose -f docker-compose.dev.yml up -d --build

# Verify containers
docker ps | grep respec-ai-dev
```

### Database Access

The development database is exposed on port 5433 for debugging:

```bash
# Connect to dev database
psql -h localhost -p 5433 -U respec -d respec_dev
# Password: respec_dev
```

### Configuration

- **Dockerfile**: `Dockerfile.dev`
- **Compose**: `docker-compose.dev.yml`
- **Database Port**: 5433 (external), 5432 (internal)
- **Debug Port**: 9876 (optional, for future debugging)
- **Environment**: Debug logging, source volumes mounted

### Stopping/Restarting

```bash
# Stop development containers
docker compose -f docker-compose.dev.yml down

# Restart with rebuild
docker compose -f docker-compose.dev.yml up -d --build

# View logs
docker compose -f docker-compose.dev.yml logs -f
```

## Production Deployment

### Purpose

End user deployment via PyPI package or Homebrew installation.

### Key Features

- Image: `respec-ai-server:latest` (pushed to ghcr.io registry)
- Container: `respec-ai-prod`
- Database: `respec-ai-db-prod` (internal only, no external exposure)
- Network: `respec-prod-network` (isolated)
- No source code volumes
- Production logging

### Setup

Production users should use the `respec-ai` CLI commands:

```bash
# Install respec-ai
pip install respec-ai
# or
brew install respec-ai

# Register MCP server with Claude Code
respec-ai register-mcp

# Start Docker containers
respec-ai docker start

# Verify status
respec-ai status
```

### Database Security

The production database is on an isolated Docker network with **no external port exposure**. This is the primary security mechanism:

- Database accessible only via internal Docker network
- No external connections possible
- Network isolation ensures container-only access

### Configuration

- **Dockerfile**: `Dockerfile.prod`
- **Compose**: `docker-compose.yml`
- **Database Port**: Internal only (no external exposure)
- **Environment**: Production logging, no debug features

### Management

```bash
# Start containers
respec-ai docker start

# Stop containers
respec-ai docker stop

# Restart containers
respec-ai docker restart

# Pull latest image
respec-ai docker pull

# View status
respec-ai status
```

## Network Architecture

### Development Network

```text
respec-dev-network (bridge)
├── respec-ai-mcp-dev (MCP server)
└── respec-ai-db-dev (PostgreSQL)
    └── Port 5433:5432 (exposed for debugging)
```

### Production Network

```text
respec-prod-network (bridge)
├── respec-ai-prod (MCP server)
└── respec-ai-db-prod (PostgreSQL)
    └── Internal only (no port exposure)
```

## Running Both Simultaneously

Development and production environments can run simultaneously without conflict:

```bash
# Start dev environment
docker compose -f docker-compose.dev.yml up -d

# Start prod environment
docker compose up -d

# Verify both running
docker ps
# Should show:
# - respec-ai-mcp-dev
# - respec-ai-db-dev
# - respec-ai-prod
# - respec-ai-db-prod

# Verify separate networks
docker network ls | grep respec
# Should show:
# - respec-dev-network
# - respec-prod-network
```

## Data Persistence

### Development Data

Stored in Docker volume: `respec_ai_dev_data`

```bash
# Backup dev data
docker run --rm -v respec_ai_dev_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/dev-data-backup.tar.gz /data

# Restore dev data
docker run --rm -v respec_ai_dev_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/dev-data-backup.tar.gz -C /
```

### Production Data

Stored in Docker volume: `respec_prod_data`

```bash
# Backup prod data
docker run --rm -v respec_prod_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/prod-data-backup.tar.gz /data

# Restore prod data
docker run --rm -v respec_prod_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/prod-data-backup.tar.gz -C /
```

## Troubleshooting

### Development Issues

**Container won't start:**
```bash
# Check logs
docker compose -f docker-compose.dev.yml logs

# Rebuild from scratch
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d --build
```

**Can't connect to database:**
```bash
# Verify db container running
docker ps | grep respec-ai-db-dev

# Check database logs
docker logs respec-ai-db-dev

# Test connection
psql -h localhost -p 5433 -U respec -d respec_dev
```

### Production Issues

**MCP server not responding:**
```bash
# Check container status
respec-ai status

# View logs
docker logs respec-ai-prod

# Restart containers
respec-ai docker restart
```

**Database connection errors:**
```bash
# Check database container
docker logs respec-ai-db-prod

# Verify network connectivity
docker network inspect respec-prod-network

# Restart both containers
respec-ai docker restart
```

### Port Conflicts

**Port 5433 already in use (dev):**
```bash
# Find what's using port 5433
lsof -i :5433

# Either stop the conflicting service or modify docker-compose.dev.yml:
# ports:
#   - "5434:5432"  # Use different external port
```

## Migration Between Versions

### Development Migration

```bash
# Pull latest code
git pull origin main

# Rebuild with new Dockerfile
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build
```

### Production Migration

```bash
# Update CLI package
respec-ai update
# or
brew upgrade respec-ai

# Pull latest Docker image and restart
respec-ai docker restart
```

## Security Considerations

### Development

- Simple password (`respec_dev`) for convenience
- Database exposed on port 5433 for debugging
- Source code mounted as volumes
- Debug logging enabled

### Production

- Database on isolated Docker network (primary security)
- No external database port exposure
- No source code volumes
- Production logging only
- Simple password fine (no sensitive data, network isolated)

## Best Practices

1. **Use appropriate environment**: Dev for development, Prod for end users
2. **Don't mix workflows**: Install script is dev-only, CLI commands are prod-only
3. **Backup data regularly**: Use volume backup commands above
4. **Monitor logs**: Check Docker logs for any issues
5. **Keep images updated**: Pull latest images periodically

## Additional Resources

- [Main README](../README.md) - Installation paths
- [Scripts README](../scripts/README.md) - Dev scripts documentation
- [CLI Guide](CLI_GUIDE.md) - Installation, setup, CLI reference, configuration
- [Workflows Guide](WORKFLOWS.md) - Detailed workflow documentation and best practices
