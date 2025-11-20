#!/bin/bash
set -e

# Specter Installation Script
# Generates Specter workflow files directly using the specter-setup CLI

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
    echo "Specter Installation Script"
    echo ""
    echo "Installs Specter workflow files to the current directory."
    echo ""
    echo "Usage:"
    echo "  Local install:   cd ~/myproject && ~/path/to/specter/scripts/install-specter.sh -n myproject -p linear"
    echo ""
    echo "  Remote install:  cd ~/myproject && curl -fsSL https://raw.githubusercontent.com/mmcclatchy/specter/main/scripts/install-specter.sh | bash -s -- -n myproject -p linear --specter-path ~/coding/projects/specter"
    echo ""
    echo "Arguments:"
    echo "  -n, --project-name   Name for this project (required)"
    echo "  -p, --platform       Platform choice: linear, github, or markdown (required)"
    echo "  --specter-path       Path to Specter installation (required for remote install only)"
    echo ""
    echo "Examples:"
    echo "  cd ~/myproject"
    echo "  ~/specter/scripts/install-specter.sh -n myproject -p linear"
    echo ""
}

# Parse arguments
parse_arguments() {
    PLATFORM=""
    SPECTER_PATH=""
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
            --specter-path)
                SPECTER_PATH="$2"
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

# Determine Specter installation path
if [ "$EXECUTION_MODE" = "local" ]; then
    # Local execution: calculate path from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SPECTER_PATH="$(dirname "$SCRIPT_DIR")"
    print_info "Detected local Specter installation: $SPECTER_PATH"
else
    # Remote execution: require --specter-path
    if [ -z "$SPECTER_PATH" ]; then
        print_error "Remote installation requires --specter-path argument"
        echo ""
        echo "Example:"
        echo "  curl -fsSL https://raw.githubusercontent.com/mmcclatchy/specter/main/scripts/install-specter.sh | bash -s -- --platform linear --specter-path ~/coding/projects/specter"
        echo ""
        echo "Make sure you have:"
        echo "  1. Cloned the Specter repository"
        echo "  2. Registered the Specter MCP server with Claude Code"
        exit 1
    fi
fi

# Validate Specter installation
if [ ! -d "$SPECTER_PATH" ]; then
    print_error "Specter directory does not exist: $SPECTER_PATH"
    exit 1
fi

if [ ! -f "$SPECTER_PATH/pyproject.toml" ]; then
    print_error "Invalid Specter installation (missing pyproject.toml): $SPECTER_PATH"
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

print_info "Specter Installation"
print_info "Execution mode: $EXECUTION_MODE"
print_info "Specter path: $SPECTER_PATH"
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
print_info "Generating Specter workflow files..."
if uv run --directory "$SPECTER_PATH" specter-setup --project-path "$TARGET_DIR" --project-name "$PROJECT_NAME" --platform "$PLATFORM"; then
    echo ""
    print_success "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to load the new commands"
    echo "  2. Start using Specter workflows:"
    echo "     • /specter-plan - Create strategic plans"
    echo "     • /specter-roadmap - Create phased roadmaps"
    echo "     • /specter-spec - Generate technical specifications"
    echo "     • /specter-build - Execute implementation"
    echo ""
else
    print_error "Installation failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify uv is installed: uv --version"
    echo "  2. Verify Specter dependencies: cd $SPECTER_PATH && uv sync"
    echo "  3. Check Specter MCP server is registered: claude mcp list"
    echo ""
    exit 1
fi
