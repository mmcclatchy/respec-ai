import logging
from typing import Any

from src.mcp import server as server_module
from src.utils.setting_configs import LogLevel, mcp_settings


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

    def fake_logging_middleware(**kwargs: Any) -> str:
        captured_logging_kwargs.update(kwargs)
        return 'logging-middleware'

    def fake_error_middleware(**_kwargs: Any) -> str:
        return 'error-middleware'

    monkeypatch.setattr(server_module, 'FastMCP', _DummyMCP)
    monkeypatch.setattr(server_module, 'LoggingMiddleware', fake_logging_middleware)
    monkeypatch.setattr(server_module, 'ErrorHandlingMiddleware', fake_error_middleware)
    monkeypatch.setattr(server_module, 'register_all_tools', lambda _mcp: None)
    monkeypatch.setattr(mcp_settings, 'log_level', level, raising=False)
    monkeypatch.setattr(mcp_settings, 'log_file', 'stdout', raising=False)

    try:
        server_module.create_mcp_server()
    finally:
        mcp_settings.log_level = previous_level
        mcp_settings.log_file = previous_log_file

    return captured_logging_kwargs


def test_create_mcp_server_disables_payload_logging_for_info(monkeypatch: Any) -> None:
    kwargs = _build_server_with_log_level(monkeypatch, LogLevel.INFO)
    assert kwargs['log_level'] == logging.INFO
    assert kwargs['include_payloads'] is True
    serializer = kwargs['payload_serializer']
    payload = serializer({'arguments': {'content': 'very secret body', 'key': 'k1'}, 'name': 'store_review_section'})
    assert 'very secret body' not in payload
    assert '<redacted:16 chars>' in payload


def test_create_mcp_server_enables_payload_logging_for_debug(monkeypatch: Any) -> None:
    kwargs = _build_server_with_log_level(monkeypatch, LogLevel.DEBUG)
    assert kwargs['log_level'] == logging.DEBUG
    assert kwargs['include_payloads'] is True
    serializer = kwargs['payload_serializer']
    payload = serializer({'arguments': {'content': 'very secret body', 'key': 'k1'}, 'name': 'store_review_section'})
    assert 'very secret body' in payload
