#!/usr/bin/env bash
set -euo pipefail

# Build script for respec-ai - Builds both CLI package and Docker image

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from pyproject.toml (single source of truth)
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${GREEN}Building respec-ai v${VERSION}${NC}"
echo ""

# Step 1: Sync version to server package
echo -e "${YELLOW}Step 1: Syncing version to server package...${NC}"
sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.server.toml
rm -f pyproject.server.toml.bak

# Verify sync
SERVER_VERSION=$(grep '^version = ' pyproject.server.toml | cut -d'"' -f2)
if [ "$VERSION" != "$SERVER_VERSION" ]; then
    echo -e "${RED}Error: Version sync failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Version synced: $VERSION${NC}"
echo ""

# Step 2: Clean old build artifacts
echo -e "${YELLOW}Step 2: Cleaning old build artifacts...${NC}"
rm -rf dist/ build/ *.egg-info
echo -e "${GREEN}✓ Cleaned${NC}"
echo ""

# Step 3: Build CLI package
echo -e "${YELLOW}Step 3: Building CLI package...${NC}"
uv build
echo -e "${GREEN}✓ CLI package built: dist/respec_ai-${VERSION}-py3-none-any.whl${NC}"
echo ""

# Step 4: Build Docker image
echo -e "${YELLOW}Step 4: Building Docker image...${NC}"
docker build -t respec-ai-server:${VERSION} .
echo -e "${GREEN}✓ Docker image built: respec-ai-server:${VERSION}${NC}"
echo ""

# Step 5: Tag Docker image as latest
echo -e "${YELLOW}Step 5: Tagging as latest...${NC}"
docker tag respec-ai-server:${VERSION} respec-ai-server:latest
echo -e "${GREEN}✓ Tagged as respec-ai-server:latest${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "CLI Package:"
echo "  - dist/respec_ai-${VERSION}-py3-none-any.whl"
echo "  - dist/respec-ai-${VERSION}.tar.gz"
echo ""
echo "Docker Images:"
echo "  - respec-ai-server:${VERSION}"
echo "  - respec-ai-server:latest"
echo ""
echo "Next steps:"
echo "  1. Test locally: uv tool install dist/respec_ai-${VERSION}-py3-none-any.whl"
echo "  2. Create git tag: git tag -a v${VERSION} -m 'Release v${VERSION}'"
echo "  3. Push tag: git push origin v${VERSION}"
echo "  4. GitHub Actions will publish to PyPI and GHCR automatically"
