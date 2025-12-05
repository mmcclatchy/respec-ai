#!/bin/bash
set -e

# RespecAI Installation Script
# Generates RespecAI workflow files directly using the respec-setup CLI

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
    echo "RespecAI Installation Script"
    echo ""
    echo "Installs RespecAI workflow files to the current directory."
    echo ""
    echo "Usage:"
    echo "  Local install:   cd ~/myproject && ~/path/to/respec-ai/scripts/install-respec-ai.sh -n myproject -p linear"
    echo ""
    echo "  Remote install:  cd ~/myproject && curl -fsSL https://raw.githubusercontent.com/mmcclatchy/respec-ai/main/scripts/install-respec-ai.sh | bash -s -- -n myproject -p linear --respec-path ~/coding/projects/respec-ai"
    echo ""
    echo "Arguments:"
    echo "  -n, --project-name   Name for this project (required)"
    echo "  -p, --platform       Platform choice: linear, github, or markdown (required)"
    echo "  --respec-path       Path to RespecAI installation (required for remote install only)"
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
}

# Parse arguments
parse_arguments "$@"

# Target directory is always current directory
TARGET_DIR="$(pwd)"

# Detect execution mode
EXECUTION_MODE=$(detect_execution_mode)

# Determine RespecAI installation path
if [ "$EXECUTION_MODE" = "local" ]; then
    # Local execution: calculate path from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    RESPEC_AI_PATH="$(dirname "$SCRIPT_DIR")"
    print_info "Detected local RespecAI installation: $RESPEC_AI_PATH"
else
    # Remote execution: require --respec-path
    if [ -z "$RESPEC_AI_PATH" ]; then
        print_error "Remote installation requires --respec-path argument"
        echo ""
        echo "Example:"
        echo "  curl -fsSL https://raw.githubusercontent.com/mmcclatchy/respec-ai/main/scripts/install-respec-ai.sh | bash -s -- --platform linear --respec-path ~/coding/projects/respec-ai"
        echo ""
        echo "Make sure you have:"
        echo "  1. Cloned the RespecAI repository"
        echo "  2. Registered the RespecAI MCP server with Claude Code"
        exit 1
    fi
fi

# Validate RespecAI installation
if [ ! -d "$RESPEC_AI_PATH" ]; then
    print_error "RespecAI directory does not exist: $RESPEC_AI_PATH"
    exit 1
fi

if [ ! -f "$RESPEC_AI_PATH/pyproject.toml" ]; then
    print_error "Invalid RespecAI installation (missing pyproject.toml): $RESPEC_AI_PATH"
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

print_info "RespecAI Installation"
print_info "Execution mode: $EXECUTION_MODE"
print_info "RespecAI path: $RESPEC_AI_PATH"
print_info "Target directory: $TARGET_DIR"
print_info "Project name: $PROJECT_NAME"
print_info "Platform: $PLATFORM"
echo ""

# Check if target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    print_error "Target directory does not exist: $TARGET_DIR"
    exit 1
fi

# Run the setup CLI
print_info "Generating RespecAI workflow files..."
if uv run --directory "$RESPEC_AI_PATH" respec-setup --project-path "$TARGET_DIR" --project-name "$PROJECT_NAME" --platform "$PLATFORM"; then
    echo ""
    print_success "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to load the new commands"
    echo "  2. Start using RespecAI workflows:"
    echo "     • /respec-plan - Create strategic plans"
    echo "     • /respec-roadmap - Create phased roadmaps"
    echo "     • /respec-spec - Generate technical specifications"
    echo "     • /respec-build - Execute implementation"
    echo ""
else
    print_error "Installation failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify uv is installed: uv --version"
    echo "  2. Verify RespecAI dependencies: cd $RESPEC_AI_PATH && uv sync"
    echo "  3. Check RespecAI MCP server is registered: claude mcp list"
    echo ""
    exit 1
fi
