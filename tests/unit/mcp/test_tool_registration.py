from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP
from pytest_mock import MockerFixture

from src.mcp.tools import register_all_tools


class TestToolRegistration:
    @pytest.fixture
    def mock_mcp(self, mocker: MockerFixture) -> MagicMock:
        return mocker.Mock(spec=FastMCP)

    def test_register_all_tools_calls_all_registration_functions(self, mock_mcp: MagicMock) -> None:
        register_all_tools(mock_mcp)

        # Verify that tools are registered by checking mcp.tool() was called
        assert mock_mcp.tool.called
        # Should have 20+ tool registrations based on server.py analysis
        assert mock_mcp.tool.call_count >= 20

    def test_register_all_tools_with_none_raises_error(self) -> None:
        with pytest.raises(AttributeError):
            register_all_tools(None)  # type: ignore

    def test_register_all_tools_handles_invalid_mcp_instance(self) -> None:
        with pytest.raises(AttributeError):
            register_all_tools('not_an_mcp_instance')  # type: ignore
