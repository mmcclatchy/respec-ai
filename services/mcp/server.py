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


class MCPRequestFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Only enhance debug logs about received messages
        if record.levelno != logging.DEBUG or 'Received message:' not in record.getMessage():
            return True

        # Extract the message object from log args
        if not record.args or len(record.args) < 1:
            return True

        # record.args is a tuple at runtime, despite type stubs saying Mapping
        message = record.args[0] if isinstance(record.args, tuple) else None
        if message is None:
            return True

        try:
            # Handle RequestResponder (requests)
            if hasattr(message, 'request') and hasattr(message.request, 'root'):
                req = message.request.root
                method = getattr(req, 'method', 'unknown')

                # Extract additional details based on method
                details = []
                if hasattr(req, 'params') and req.params:
                    if hasattr(req.params, 'name'):
                        details.append(f'name={req.params.name}')
                    if hasattr(req.params, 'uri'):
                        details.append(f'uri={req.params.uri}')

                detail_str = f', {", ".join(details)}' if details else ''
                record.msg = f'Received request: method={method}{detail_str}'
                record.args = ()

            # Handle ClientNotification (notifications)
            elif hasattr(message, 'root') and hasattr(message.root, 'method'):
                method = message.root.method
                record.msg = f'Received notification: method={method}'
                record.args = ()

            # Handle exceptions
            elif isinstance(message, Exception):
                record.msg = f'Received exception: {type(message).__name__}: {message}'
                record.args = ()

        except Exception as e:
            # If extraction fails, allow original log through
            logging.getLogger(__name__).warning(f'Failed to enhance MCP log: {e}', exc_info=True)

        return True


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
            # Make relative paths relative to the spec-ai project directory
            log_path = Path(__file__).parent.parent.parent / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
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

    # Configure third-party loggers
    logging.getLogger('markdown_it').setLevel(logging.WARNING)

    # Add custom filter to MCP lowlevel server logger to extract useful request info
    mcp_server_logger = logging.getLogger('mcp.server.lowlevel.server')
    mcp_server_logger.setLevel(log_level)  # Allow DEBUG logs through
    mcp_server_logger.addFilter(MCPRequestFilter())

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
            max_payload_length=50000,
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
