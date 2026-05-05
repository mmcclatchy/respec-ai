import logging
import sys
import json
import time
from typing import Any, Callable
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware, default_serializer

from src.mcp.lifespan import mcp_lifespan
from src.mcp.tools import register_all_tools
from src.utils.enums import HealthState
from src.utils.loop_state import HealthStatus
from src.utils.setting_configs import LogPayloadMode, mcp_settings


REDACTED_PAYLOAD_KEYS = {
    'content',
    'analysis',
    'feedback_markdown',
    'detailed_feedback',
}


def _redact_payload_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in REDACTED_PAYLOAD_KEYS and isinstance(item, str):
                redacted[key] = f'<redacted:{len(item)} chars>'
            else:
                redacted[key] = _redact_payload_value(item)
        return redacted

    if isinstance(value, list):
        return [_redact_payload_value(item) for item in value]

    return value


def _build_payload_serializer(include_full_payloads: bool) -> Callable[[Any], str]:
    def payload_serializer(message: Any) -> str:
        serialized = default_serializer(message)

        if include_full_payloads:
            return serialized

        try:
            parsed = json.loads(serialized)
        except Exception:
            return serialized

        return json.dumps(_redact_payload_value(parsed))

    return payload_serializer


def _get_message_value(message: Any, key: str) -> Any:
    if isinstance(message, dict):
        return message.get(key)
    return getattr(message, key, None)


def _metadata_length(value: Any) -> str:
    try:
        return str(len(value))
    except Exception:
        return 'unknown'


def _summarize_metadata_value(key: str, value: Any, depth: int = 0) -> Any:
    if key.lower() in REDACTED_PAYLOAD_KEYS:
        value_type = type(value).__name__
        return f'<redacted:{_metadata_length(value)} {value_type}>'

    if isinstance(value, str):
        return value if len(value) <= 200 else f'{value[:200]}...'

    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, dict):
        keys = sorted(str(item_key) for item_key in value)
        if depth >= 2:
            return {'type': 'dict', 'keys': keys, 'size': len(value)}
        return {
            str(item_key): _summarize_metadata_value(str(item_key), item_value, depth + 1)
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        item_types = sorted({type(item).__name__ for item in value[:10]})
        return {'type': 'list', 'size': len(value), 'item_types': item_types}

    if isinstance(value, tuple | set):
        item_types = sorted({type(item).__name__ for item in list(value)[:10]})
        return {'type': type(value).__name__, 'size': len(value), 'item_types': item_types}

    return {'type': type(value).__name__}


def _summarize_message_metadata(message: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {'message_type': type(message).__name__}

    name = _get_message_value(message, 'name')
    if name is not None:
        metadata['tool_name'] = str(name)

    uri = _get_message_value(message, 'uri')
    if uri is not None:
        metadata['uri'] = str(uri)

    arguments = _get_message_value(message, 'arguments')
    if isinstance(arguments, dict):
        metadata['argument_keys'] = sorted(str(key) for key in arguments)
        metadata['arguments'] = {
            str(key): _summarize_metadata_value(str(key), value) for key, value in arguments.items()
        }
    elif arguments is not None:
        metadata['arguments'] = {'type': type(arguments).__name__}

    return metadata


class MetadataLoggingMiddleware(Middleware):
    def __init__(
        self,
        *,
        logger: logging.Logger,
        log_level: int = logging.INFO,
        methods: list[str] | None = None,
    ) -> None:
        self.logger = logger
        self.log_level = log_level
        self.methods = methods

    async def on_message(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        if self.methods and context.method not in self.methods:
            return await call_next(context)

        metadata = _summarize_message_metadata(context.message)
        self.logger.log(
            self.log_level,
            'event=%s method=%s source=%s metadata=%s',
            f'{context.type}_start',
            context.method or 'unknown',
            context.source,
            metadata,
        )

        start_time = time.perf_counter()
        try:
            result = await call_next(context)
            self.logger.log(
                self.log_level,
                'event=%s method=%s source=%s duration_ms=%.3f status=success',
                f'{context.type}_success',
                context.method or 'unknown',
                context.source,
                (time.perf_counter() - start_time) * 1000,
            )
            return result
        except Exception as e:
            self.logger.error(
                'event=%s method=%s source=%s duration_ms=%.3f status=error error=%s',
                f'{context.type}_error',
                context.method or 'unknown',
                context.source,
                (time.perf_counter() - start_time) * 1000,
                e,
            )
            raise


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
            # Make relative paths relative to the respec-ai project directory
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
    payload_mode = mcp_settings.log_payload_mode

    mcp = FastMCP(mcp_settings.server_name, lifespan=mcp_lifespan)
    error_logger = logging.getLogger('mcp_errors')

    def handle_error(error: Exception, context: MiddlewareContext) -> None:
        error_logger.error('=' * 60)
        error_logger.error('MCP REQUEST ERROR')
        error_logger.error(f'Method: {context.method}')
        error_logger.error(f'Error Type: {type(error).__name__}')
        error_logger.error(f'Error Message: {error}')

        # Show traceback if debug mode OR log level is DEBUG
        show_traceback = mcp_settings.debug or mcp_settings.log_level == 'DEBUG'

        if show_traceback:
            error_logger.error('=' * 60)
            error_logger.exception('Full traceback:')
        else:
            error_logger.error('=' * 60)
            error_logger.error('(Enable DEBUG mode for full traceback: Set MCP_DEBUG=true or MCP_LOG_LEVEL=DEBUG)')
        error_logger.error('=' * 60)

    mcp.add_middleware(
        ErrorHandlingMiddleware(
            include_traceback=mcp_settings.debug, transform_errors=True, error_callback=handle_error
        )
    )

    if payload_mode == LogPayloadMode.METADATA:
        mcp.add_middleware(MetadataLoggingMiddleware(logger=tool_logger, log_level=log_level))
    else:
        include_full_payloads = payload_mode == LogPayloadMode.FULL
        mcp.add_middleware(
            LoggingMiddleware(
                logger=tool_logger,
                log_level=log_level,
                include_payloads=True,
                max_payload_length=50000,
                payload_serializer=_build_payload_serializer(include_full_payloads),
            )
        )

    # Register all tools
    register_all_tools(mcp)

    return mcp


def _log_server_startup(logger: logging.Logger, transport: str) -> None:
    logger.info('=' * 60)
    logger.info('respec-ai MCP Server Starting')
    logger.info(f'Server Name: {mcp_settings.server_name}')
    logger.info(f'Transport: {transport}')
    logger.info(f'Working Directory: {Path.cwd()}')
    logger.info(f'Log Level: {mcp_settings.log_level}')
    logger.info(f'Log Payload Mode: {mcp_settings.log_payload_mode}')
    logger.info(f'Debug Mode: {mcp_settings.debug}')
    logger.info('=' * 60)


def run_local_server() -> None:
    logger = logging.getLogger(__name__)

    try:
        server = create_mcp_server()
        _log_server_startup(logger, 'stdio')
        logger.info('MCP Server initialized successfully')
        logger.info('Waiting for client connection...')

        server.run(transport='stdio')

    except KeyboardInterrupt:
        logger.info('MCP Server shutdown requested')
        sys.exit(0)
    except Exception as e:
        logger.error('=' * 60)
        logger.error('FATAL ERROR: MCP Server failed')
        logger.error(f'Error Type: {type(e).__name__}')
        logger.error(f'Error Message: {e}')
        logger.error(f'Working Directory: {Path.cwd()}')
        logger.error('=' * 60)
        if mcp_settings.debug:
            logger.exception('Full traceback:')
        sys.exit(1)


def run_http_server() -> None:
    logger = logging.getLogger(__name__)

    try:
        server = create_mcp_server()
        _log_server_startup(logger, 'streamable-http')
        logger.info('MCP Server initialized successfully')
        logger.info(f'Listening on {mcp_settings.host}:{mcp_settings.port}/mcp')

        server.run(
            transport='streamable-http',
            host=mcp_settings.host,
            port=mcp_settings.port,
            path='/mcp',
        )

    except KeyboardInterrupt:
        logger.info('MCP Server shutdown requested')
        sys.exit(0)
    except Exception as e:
        logger.error('=' * 60)
        logger.error('FATAL ERROR: MCP HTTP Server failed')
        logger.error(f'Error Type: {type(e).__name__}')
        logger.error(f'Error Message: {e}')
        logger.error(f'Working Directory: {Path.cwd()}')
        logger.error('=' * 60)
        if mcp_settings.debug:
            logger.exception('Full traceback:')
        sys.exit(1)


async def health_check(server: FastMCP) -> HealthStatus:
    try:
        tools = await server.list_tools()
        return HealthStatus(status=HealthState.HEALTHY, tools_count=len(tools))
    except Exception as e:
        return HealthStatus(status=HealthState.UNHEALTHY, error=str(e))
