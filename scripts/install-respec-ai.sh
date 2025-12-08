#!/bin/bash
set -e

# respec-ai Installation Script
# Generates respec-ai workflow files in the current directory using respec-ai init

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Detect if running via curl (remote) or direct execution (local)
detect_execution_mode() {
    if [ -n "$BASH_SOURCE" ] && [ -f "$BASH_SOURCE" ]; then
        echo "local"
    else
        echo "remote"
    fi
}

# Show usage information
show_usage() {
    echo ""
    echo "respec-ai Installation Script"
    echo ""
    echo "Installs respec-ai workflow files to the current directory."
    echo ""
    echo "Usage:"
    echo "  Local install:   cd ~/myproject && ~/path/to/respec-ai/scripts/install-respec-ai.sh -n myproject -p linear"
    echo ""
    echo "  Remote install:  cd ~/myproject && curl -fsSL https://raw.githubusercontent.com/mmcclatchy/respec-ai/main/scripts/install-respec-ai.sh | bash -s -- -n myproject -p linear --respec-path ~/coding/projects/respec-ai"
    echo ""
    echo "Arguments:"
    echo "  -n, --project-name   Name for this project (required)"
    echo "  -p, --platform       Platform choice: linear, github, or markdown (required)"
    echo "  --respec-path       Path to respec-ai installation (required for remote install only)"
    echo ""
    echo "Examples:"
    echo "  cd ~/myproject"
    echo "  ~/respec-ai/scripts/install-respec-ai.sh -n myproject -p linear"
    echo ""
}

# Parse arguments
parse_arguments() {
    PLATFORM=""
    RESPEC_AI_PATH=""
    PROJECT_NAME=""
    STATE_MANAGER="memory"  # Default to memory

    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--project-name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            --state-manager)
                STATE_MANAGER="$2"
                shift 2
                ;;
            --respec-path)
                RESPEC_AI_PATH="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$PROJECT_NAME" ]; then
        print_error "Project name is required. Use -n <name> or --project-name <name>"
        show_usage
        exit 1
    fi

    if [ -z "$PLATFORM" ]; then
        print_error "Platform is required. Use -p linear|github|markdown or --platform linear|github|markdown"
        show_usage
        exit 1
    fi

    # Validate state manager
    if [[ ! "$STATE_MANAGER" =~ ^(memory|database)$ ]]; then
        print_error "Invalid state manager: $STATE_MANAGER"
        echo "State manager must be one of: memory, database"
        exit 1
    fi
}

# Parse arguments
parse_arguments "$@"

# Target directory is always current directory
TARGET_DIR="$(pwd)"

# Detect execution mode
EXECUTION_MODE=$(detect_execution_mode)

# Determine respec-ai installation path
if [ "$EXECUTION_MODE" = "local" ]; then
    # Local execution: calculate path from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    RESPEC_AI_PATH="$(dirname "$SCRIPT_DIR")"
    print_info "Detected local respec-ai installation: $RESPEC_AI_PATH"
else
    # Remote execution: require --respec-path
    if [ -z "$RESPEC_AI_PATH" ]; then
        print_error "Remote installation requires --respec-path argument"
        echo ""
        echo "Example:"
        echo "  curl -fsSL https://raw.githubusercontent.com/mmcclatchy/respec-ai/main/scripts/install-respec-ai.sh | bash -s -- --platform linear --respec-path ~/coding/projects/respec-ai"
        echo ""
        echo "Make sure you have:"
        echo "  1. Cloned the respec-ai repository"
        echo "  2. Registered the respec-ai MCP server with Claude Code"
        exit 1
    fi
fi

# Validate respec-ai installation
if [ ! -d "$RESPEC_AI_PATH" ]; then
    print_error "respec-ai directory does not exist: $RESPEC_AI_PATH"
    exit 1
fi

if [ ! -f "$RESPEC_AI_PATH/pyproject.toml" ]; then
    print_error "Invalid respec-ai installation (missing pyproject.toml): $RESPEC_AI_PATH"
    exit 1
fi

# Validate platform
if [[ ! "$PLATFORM" =~ ^(linear|github|markdown)$ ]]; then
    print_error "Invalid platform: $PLATFORM"
    echo "Platform must be one of: linear, github, markdown"
    exit 1
fi

# Convert to absolute path
TARGET_DIR=$(cd "$TARGET_DIR" && pwd)

print_info "respec-ai Installation"
print_info "Execution mode: $EXECUTION_MODE"
print_info "respec-ai path: $RESPEC_AI_PATH"
print_info "Target directory: $TARGET_DIR"
print_info "Project name: $PROJECT_NAME"
print_info "Platform: $PLATFORM"
echo ""

# Check if target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    print_error "Target directory does not exist: $TARGET_DIR"
    exit 1
fi

# Configure state manager mode
if [ "$STATE_MANAGER" = "memory" ]; then
    print_info "State Manager: In-Memory (clean slate on restart)"
    STATE_MANAGER_MODE="memory"
    MCP_COMMAND="uv"
    MCP_ARGS='["run", "respec-server"]'
elif [ "$STATE_MANAGER" = "database" ]; then
    print_info "State Manager: Database (persistent state)"

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required for database mode"
        echo "Install Docker Desktop or docker-compose"
        exit 1
    fi

    # Start Docker Compose services
    print_info "Starting database and MCP server containers..."
    cd "$RESPEC_AI_PATH"
    docker compose -f docker-compose.dev.yml up -d

    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 5

    # Run database migrations
    print_info "Running database migrations..."
    if docker compose -f docker-compose.dev.yml exec -T db psql -U respec -d respec_dev -f /docker-entrypoint-initdb.d/001_initial_schema.sql 2>/dev/null; then
        print_success "Schema migration applied"
        docker compose -f docker-compose.dev.yml exec -T db psql -U respec -d respec_dev -f /docker-entrypoint-initdb.d/002_add_indexes.sql 2>/dev/null
        print_success "Index migration applied"
    else
        print_info "Migrations already applied (skipping)"
    fi

    STATE_MANAGER_MODE="database"
    MCP_COMMAND="docker"
    MCP_ARGS='["compose", "-f", "'"$RESPEC_AI_PATH/docker-compose.dev.yml"'", "exec", "-T", "mcp-server", "respec-server"]'

    cd "$TARGET_DIR"
fi

echo ""

# Run the setup CLI (skip MCP registration - we'll register local version manually)
print_info "Generating respec-ai workflow files..."
if uv run --directory "$RESPEC_AI_PATH" respec-ai init --project-name "$PROJECT_NAME" --platform "$PLATFORM" --skip-mcp-registration --force; then
    echo ""

    # Register local MCP server in Claude Code
    print_info "Registering local MCP server in Claude Code..."

    # Remove existing registration if present
    claude mcp remove respec-ai 2>/dev/null || true

    # Register MCP server using Claude CLI with explicit directory path
    if [ "$STATE_MANAGER" = "memory" ]; then
        if claude mcp add -s user -t stdio respec-ai -- uv --directory "$RESPEC_AI_PATH" run python -m src.mcp; then
            print_success "✓ Registered local MCP server (state: $STATE_MANAGER_MODE, path: $RESPEC_AI_PATH)"
        else
            print_error "✗ Failed to register MCP server"
            exit 1
        fi
    else
        # Database mode - use docker compose command
        if claude mcp add -s user -t stdio respec-ai -- docker compose -f "$RESPEC_AI_PATH/docker-compose.dev.yml" exec -T mcp-server respec-server; then
            print_success "✓ Registered local MCP server (state: $STATE_MANAGER_MODE, database mode)"
        else
            print_error "✗ Failed to register MCP server"
            exit 1
        fi
    fi

    # Add MCP permissions to Claude settings
    print_info "Adding MCP permissions to Claude settings..."
    if uv run --directory "$RESPEC_AI_PATH" python -c "from src.cli.config.claude_config import add_mcp_permissions; add_mcp_permissions()"; then
        print_success "✓ MCP permissions added"
    else
        print_warning "⚠ Failed to add MCP permissions (you may need to add manually)"
    fi

    if [ $? -eq 0 ]; then
        echo ""
        print_success "Installation complete!"
        echo ""
        print_info "Local Development Mode Active"
        echo "  • MCP server runs from: $RESPEC_AI_PATH"
        echo "  • State manager: $STATE_MANAGER_MODE"
        echo "  • Changes take effect after restarting Claude Code"
        if [ "$STATE_MANAGER" = "memory" ]; then
            echo "  • No Docker required (in-memory state)"
        else
            echo "  • Database running in Docker (persistent state)"
        fi
        echo ""
        echo "Next steps:"
        echo "  1. Restart Claude Code to load the new commands"
        echo "  2. Verify MCP server: /mcp list"
        echo "  3. Start using respec-ai workflows:"
        echo "     • /respec-plan - Create strategic plans"
        echo "     • /respec-roadmap - Create phased roadmaps"
        echo "     • /respec-spec - Generate technical specifications"
        echo "     • /respec-build - Execute implementation"
        echo ""
    else
        print_warning "Workflow files created but MCP registration failed"
        echo ""
        echo "Manual registration:"
        echo "  Run this command:"
        echo ""
        if [ "$STATE_MANAGER" = "memory" ]; then
            echo "  claude mcp add -s user -t stdio respec-ai -- uv --directory $RESPEC_AI_PATH run python -m src.mcp"
        else
            echo "  claude mcp add -s user -t stdio respec-ai -- docker compose -f $RESPEC_AI_PATH/docker-compose.dev.yml exec -T mcp-server respec-server"
        fi
        echo ""
    fi
else
    print_error "Installation failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify uv is installed: uv --version"
    echo "  2. Verify respec-ai dependencies: cd $RESPEC_AI_PATH && uv sync"
    echo "  3. Check Python is available: python3 --version"
    echo ""
    exit 1
fi
