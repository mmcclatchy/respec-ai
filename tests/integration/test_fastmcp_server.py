import pytest
from fastmcp import FastMCP

from src.mcp.server import create_mcp_server, health_check
from src.mcp.tools.loop_tools import LoopTools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import HealthState, LoopStatus
from src.utils.loop_state import HealthStatus
from src.utils.state_manager import InMemoryStateManager
from src.utils.setting_configs import mcp_settings


@pytest.fixture
def plan_name() -> str:
    return 'test-project'


class TestFastMCPServerIntegration:
    def test_fastmcp_server_initialization(self) -> None:
        server = create_mcp_server()
        assert isinstance(server, FastMCP)
        assert server.name == 'respec-ai'

    @pytest.mark.asyncio
    async def test_mcp_tool_registration(self) -> None:
        server = create_mcp_server()

        # Check that all MCP tools are registered (loop + unified document tools)
        tools_list = await server.list_tools()
        tool_names = {t.name for t in tools_list}
        expected_loop_tools = [
            'decide_loop_next_action',
            'initialize_refinement_loop',
            'get_loop_status',
            'list_active_loops',
            'get_loop_feedback_summary',
        ]
        expected_document_tools = [
            'store_document',
            'get_document',
            'update_document',
            'delete_document',
            'link_loop_to_document',
            'list_documents',
        ]
        expected_tools = expected_loop_tools + expected_document_tools

        for tool_name in expected_tools:
            assert tool_name in tool_names

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
        tools_list = await server.list_tools()

        decide_tool = next((t for t in tools_list if t.name == 'decide_loop_next_action'), None)
        assert decide_tool is not None
        assert decide_tool.description is not None
        assert decide_tool.name == 'decide_loop_next_action'

    @pytest.mark.asyncio
    async def test_error_handling_at_server_level(self, isolated_loop_tools: LoopTools) -> None:
        # Test calling tool with invalid loop_id directly through the tool function
        # This avoids using private FastMCP methods
        with pytest.raises(Exception):  # Should raise LoopNotFoundError
            await isolated_loop_tools.decide_loop_next_action('nonexistent-id')

    @pytest.mark.asyncio
    async def test_tool_parameter_validation_through_fastmcp(
        self, isolated_loop_tools: LoopTools, isolated_state_manager: InMemoryStateManager, plan_name: str
    ) -> None:
        # Test with valid parameters using new API
        init_result = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'plan')

        # Add feedback with high score
        loop_state = await isolated_state_manager.get_loop(init_result.id)
        feedback = CriticFeedback(
            loop_id=init_result.id,
            critic_agent=CriticAgent.PLAN_CRITIC,
            iteration=1,
            overall_score=90,
            assessment_summary='High quality plan',
            detailed_feedback='Plan meets all standards',
            key_issues=[],
            recommendations=[],
        )
        loop_state.add_feedback(feedback)

        result = await isolated_loop_tools.decide_loop_next_action(init_result.id)

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
        assert health_status.tools_count >= 11  # At least 5 loop + 6 document tools
        assert health_status.error is None
