# Development Scripts

## ⚠️ IMPORTANT: DEV-ONLY SCRIPTS ⚠️

**These scripts are for developers who have cloned the respec-ai repository.**

**NOT for end users who installed via PyPI or Homebrew.**

## Purpose

The scripts in this directory are development tools for contributors working on the respec-ai codebase. They are **excluded from the PyPI package** and are not available to end users.

## For End Users

If you installed respec-ai via PyPI or Homebrew, use the CLI commands instead:

```bash
# Install respec-ai
pip install respec-ai
# or
brew install respec-ai

# Register MCP server with Claude Code
respec-ai register-mcp

# Manage Docker containers
respec-ai docker start
respec-ai docker stop
respec-ai docker restart
respec-ai docker pull

# Check status
respec-ai status

# See all commands
respec-ai --help
```

For full documentation, see:
- [CLI Guide](../docs/CLI_GUIDE.md)
- [Docker Deployment Guide](../docs/DOCKER_DEPLOYMENT.md)

## For Developers

If you're a contributor who has cloned this repository, these scripts help with local development setup.

### Available Scripts

#### `install-respec-ai.sh`

Installs the respec-ai MCP server for local development.

**Usage:**
```bash
./scripts/install-respec-ai.sh
```

**What it does:**
1. Builds and starts the development Docker containers
2. Configures the MCP server for Claude Code (development mode)
3. Sets up database state management

**Configuration:**
- Uses `docker-compose.dev.yml`
- Builds `respec-ai-dev` image
- Starts `respec-ai-mcp-dev` and `respec-ai-db-dev` containers
- Database exposed on port 5433 for debugging

#### Other Scripts

Additional scripts may be added for development tasks such as:
- Database migrations
- Test data generation
- Development environment setup
- Build verification

## Development vs Production Paths

### Development Path (You're Here)

```text
Clone repo → Run install script → Use docker-compose.dev.yml → Local containers
```

- **Who**: Contributors working on respec-ai codebase
- **How**: Clone repo, run `./scripts/install-respec-ai.sh`
- **Containers**: `respec-ai-dev`, `respec-ai-db-dev`
- **Database**: Port 5433 exposed for debugging
- **Source**: Mounted as volumes for live reloading

### Production Path (End Users)

```text
pip/brew install → respec-ai CLI → docker-compose.yml → Production containers
```

- **Who**: End users installing respec-ai for Claude Code
- **How**: `pip install respec-ai` or `brew install respec-ai`
- **Containers**: `respec-ai-server`, `respec-ai-db-prod`
- **Database**: Internal network only (no external exposure)
- **Source**: Baked into image (no volumes)

## Complete Separation

These two paths are **completely separate**:

- Different Docker images (`respec-ai-dev` vs `respec-ai-server`)
- Different container names (`-dev` vs `-prod` suffix)
- Different networks (`respec-dev-network` vs `respec-prod-network`)
- Different database configurations
- Zero crossover or interference

## Excluded from Package

The `scripts/` directory is excluded from the PyPI package via `.dockerignore`. End users installing via PyPI or Homebrew will **never see these scripts** and should use the CLI commands instead.

## Contributing

If you're adding new development scripts:

1. Place them in this directory
2. Make them executable: `chmod +x scripts/your-script.sh`
3. Document them in this README
4. Ensure they're excluded from PyPI package (check `.dockerignore`)
5. Add appropriate error messages if run in wrong context

## Support

- **For development setup issues**: Open issue on GitHub
- **For end user CLI issues**: See [CLI Guide](../docs/CLI_GUIDE.md)
- **For Docker deployment questions**: See [Docker Deployment Guide](../docs/DOCKER_DEPLOYMENT.md)
