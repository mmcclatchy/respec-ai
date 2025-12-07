import pytest
from fastmcp import FastMCP

from src.mcp.server import create_mcp_server, health_check
from src.mcp.tools.loop_tools import loop_tools
from src.utils.enums import HealthState, LoopStatus
from src.utils.loop_state import HealthStatus
from src.utils.setting_configs import mcp_settings


@pytest.fixture
def project_name() -> str:
    return 'test-project'


class TestFastMCPServerIntegration:
    def test_fastmcp_server_initialization(self) -> None:
        server = create_mcp_server()
        assert isinstance(server, FastMCP)
        assert server.name == 'respec-ai'

    @pytest.mark.asyncio
    async def test_mcp_tool_registration(self) -> None:
        server = create_mcp_server()

        # Check that all MCP tools are registered (loop + roadmap tools)
        tools = await server.get_tools()
        expected_loop_tools = [
            'decide_loop_next_action',
            'initialize_refinement_loop',
            'get_loop_status',
            'list_active_loops',
            'get_previous_objective_feedback',
            'store_current_objective_feedback',
        ]
        expected_unified_tools = [
            'create_roadmap',
            'get_roadmap',
            'store_spec',
            'get_spec_markdown',
            'link_loop_to_spec',
            'unlink_loop',
            'list_specs',
            'delete_spec',
        ]
        expected_tools = expected_loop_tools + expected_unified_tools

        for tool_name in expected_tools:
            assert tool_name in tools
            assert tools[tool_name].name == tool_name

    def test_production_server_creation(self) -> None:
        # Test server configuration
        assert mcp_settings.server_name == 'respec-ai'
        assert mcp_settings.host == '0.0.0.0'
        assert mcp_settings.port == 8000

        # Test server creation
        server = create_mcp_server()
        assert isinstance(server, FastMCP)
        assert server.name == 'respec-ai'

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery_and_metadata(self) -> None:
        server = create_mcp_server()
        tools = await server.get_tools()

        # Find decide_loop_next_action tool
        decide_tool = tools.get('decide_loop_next_action')
        assert decide_tool is not None
        assert decide_tool.description is not None
        assert decide_tool.name == 'decide_loop_next_action'

    @pytest.mark.asyncio
    async def test_error_handling_at_server_level(self) -> None:
        # Test calling tool with invalid loop_id directly through the tool function
        # This avoids using private FastMCP methods
        with pytest.raises(Exception):  # Should raise LoopNotFoundError
            await loop_tools.decide_loop_next_action('nonexistent-id', 80)

    @pytest.mark.asyncio
    async def test_tool_parameter_validation_through_fastmcp(self, project_name: str) -> None:
        # Test with valid parameters using new API
        init_result = await loop_tools.initialize_refinement_loop(project_name, 'plan')
        result = await loop_tools.decide_loop_next_action(init_result.id, 90)

        assert result.status == LoopStatus.COMPLETED

    def test_server_configuration_via_pydantic_settings(self) -> None:
        assert mcp_settings.server_name == 'respec-ai'
        assert mcp_settings.host == '0.0.0.0'
        assert mcp_settings.port == 8000
        assert mcp_settings.debug is False

    @pytest.mark.asyncio
    async def test_health_check_endpoints(self) -> None:
        server = create_mcp_server()
        health_status = await health_check(server)

        assert isinstance(health_status, HealthStatus)
        assert health_status.status == HealthState.HEALTHY
        assert health_status.tools_count >= 13  # At least 6 loop + 7 roadmap tools
        assert health_status.error is None
