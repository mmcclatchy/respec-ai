import logging
import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

from services.mcp.tools import register_all_tools
from services.utils.enums import HealthState
from services.utils.loop_state import HealthStatus
from services.utils.setting_configs import mcp_settings


def _configure_logging() -> logging.Logger:
    log_level = getattr(logging, mcp_settings.log_level.upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers: list[logging.Handler] = []

    # Determine logging destination based on configuration
    if mcp_settings.log_file == 'stdout':
        # Container mode: log to stdout only
        handlers.append(logging.StreamHandler(sys.stdout))
        print(f'[MCP Server] Logging to stdout (level={mcp_settings.log_level})', file=sys.stderr, flush=True)
    elif mcp_settings.log_file:
        # File logging mode (local development)
        log_path = Path(mcp_settings.log_file)
        if not log_path.is_absolute():
            # Make relative paths relative to the specter project directory
            log_path = Path(__file__).parent.parent.parent / log_path
        handlers.append(logging.FileHandler(log_path, mode='a'))
        handlers.append(logging.StreamHandler(sys.stderr))  # Also log to stderr
        print(f'[MCP Server] Logging to file: {log_path} (level={mcp_settings.log_level})', file=sys.stderr, flush=True)
    else:
        # Stderr only (minimal mode)
        handlers.append(logging.StreamHandler(sys.stderr))
        print(f'[MCP Server] Logging to stderr (level={mcp_settings.log_level})', file=sys.stderr, flush=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Create dedicated logger for MCP tool calls
    tool_logger = logging.getLogger('mcp_tools')
    tool_logger.setLevel(log_level)

    return tool_logger


def create_mcp_server() -> FastMCP:
    tool_logger = _configure_logging()
    log_level = getattr(logging, mcp_settings.log_level.upper(), logging.INFO)

    mcp = FastMCP(mcp_settings.server_name)
    error_logger = logging.getLogger('mcp_errors')

    def handle_error(error: Exception, context: MiddlewareContext) -> None:
        error_logger.error(f'MCP Error: {type(error).__name__} in {context.method}: {error}')

    mcp.add_middleware(
        ErrorHandlingMiddleware(
            include_traceback=mcp_settings.debug, transform_errors=True, error_callback=handle_error
        )
    )

    mcp.add_middleware(
        LoggingMiddleware(
            logger=tool_logger,
            log_level=log_level,
            include_payloads=True,
            max_payload_length=500,
        )
    )

    # Register all tools
    register_all_tools(mcp)

    return mcp


def run_local_server() -> None:
    server = create_mcp_server()
    server.run(transport='stdio')


async def health_check(server: FastMCP) -> HealthStatus:
    try:
        tools = await server.get_tools()
        return HealthStatus(status=HealthState.HEALTHY, tools_count=len(tools))
    except Exception as e:
        return HealthStatus(status=HealthState.UNHEALTHY, error=str(e))
