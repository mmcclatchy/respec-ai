import logging
from typing import Any

from src.mcp import server as server_module
from src.utils.setting_configs import LogLevel, LogPayloadMode, mcp_settings


class _DummyMCP:
    def __init__(self, _name: str, lifespan: Any) -> None:
        self.lifespan = lifespan
        self.middlewares: list[Any] = []

    def add_middleware(self, middleware: Any) -> None:
        self.middlewares.append(middleware)


def _build_server_with_log_level(monkeypatch: Any, level: LogLevel) -> dict[str, Any]:
    captured_logging_kwargs: dict[str, Any] = {}
    previous_level = mcp_settings.log_level
    previous_log_file = mcp_settings.log_file
    previous_payload_mode = mcp_settings.log_payload_mode

    def fake_metadata_middleware(**kwargs: Any) -> str:
        captured_logging_kwargs.update(kwargs)
        return 'metadata-logging-middleware'

    def fake_error_middleware(**_kwargs: Any) -> str:
        return 'error-middleware'

    monkeypatch.setattr(server_module, 'FastMCP', _DummyMCP)
    monkeypatch.setattr(server_module, 'MetadataLoggingMiddleware', fake_metadata_middleware)
    monkeypatch.setattr(server_module, 'ErrorHandlingMiddleware', fake_error_middleware)
    monkeypatch.setattr(server_module, 'register_all_tools', lambda _mcp: None)
    monkeypatch.setattr(mcp_settings, 'log_level', level, raising=False)
    monkeypatch.setattr(mcp_settings, 'log_file', 'stdout', raising=False)
    monkeypatch.setattr(mcp_settings, 'log_payload_mode', LogPayloadMode.METADATA, raising=False)

    try:
        server_module.create_mcp_server()
    finally:
        mcp_settings.log_level = previous_level
        mcp_settings.log_file = previous_log_file
        mcp_settings.log_payload_mode = previous_payload_mode

    return captured_logging_kwargs


def test_create_mcp_server_uses_metadata_logging_by_default(monkeypatch: Any) -> None:
    kwargs = _build_server_with_log_level(monkeypatch, LogLevel.INFO)
    assert kwargs['log_level'] == logging.INFO


def test_create_mcp_server_metadata_logging_honors_debug_level(monkeypatch: Any) -> None:
    kwargs = _build_server_with_log_level(monkeypatch, LogLevel.DEBUG)
    assert kwargs['log_level'] == logging.DEBUG


def test_metadata_payload_summary_omits_content_fields() -> None:
    metadata = server_module._summarize_message_metadata(
        {
            'name': 'store_reviewer_result',
            'arguments': {
                'loop_id': 'loop-1',
                'review_iteration': 2,
                'feedback_markdown': '# private reviewer body',
                'detailed_feedback': 'private details',
                'analysis': 'private analysis',
                'content': 'private content',
                'score': 24,
            },
        }
    )

    rendered = str(metadata)
    assert metadata['tool_name'] == 'store_reviewer_result'
    assert metadata['argument_keys'] == [
        'analysis',
        'content',
        'detailed_feedback',
        'feedback_markdown',
        'loop_id',
        'review_iteration',
        'score',
    ]
    assert 'loop-1' in rendered
    assert 'private reviewer body' not in rendered
    assert 'private details' not in rendered
    assert 'private analysis' not in rendered
    assert 'private content' not in rendered
    assert '<redacted:' in rendered


def test_redacted_payload_serializer_omits_content_fields() -> None:
    serializer = server_module._build_payload_serializer(include_full_payloads=False)
    payload = serializer({'arguments': {'content': 'very secret body', 'key': 'k1'}, 'name': 'store_review_section'})
    assert 'very secret body' not in payload
    assert '<redacted:16 chars>' in payload
