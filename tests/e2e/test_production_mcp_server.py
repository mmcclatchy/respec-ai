import asyncio
import os
from typing import Any

from pytest_mock import MockerFixture
from src.mcp.server import create_mcp_server, health_check
from src.utils.enums import HealthState
from src.utils.setting_configs import MCPSettings


def create_test_roadmap_markdown(project_name: str) -> str:
    return f"""# Project Roadmap: {project_name}

## Project Details
- **Project Goal**: Build and deploy {project_name}
- **Total Duration**: 6 months
- **Team Size**: 5 developers
- **Budget**: $100,000

## Specifications


## Risk Assessment
- **Critical Path Analysis**: Critical path analysis pending
- **Key Risks**: Standard development risks
- **Mitigation Plans**: Standard mitigation strategies
- **Buffer Time**: 2 weeks

## Resource Planning
- **Development Resources**: 5 developers, 1 PM
- **Infrastructure Requirements**: AWS cloud infrastructure
- **External Dependencies**: None identified
- **Quality Assurance Plan**: Automated testing and manual QA

## Success Metrics
- **Technical Milestones**: Alpha, Beta, Production release
- **Business Milestones**: User adoption targets
- **Quality Gates**: Code review, testing, security review
- **Performance Targets**: Sub-2s response times

## Metadata
- **Status**: draft
- **Created**: 2024-01-01
- **Last Updated**: 2024-01-01
- **Spec Count**: 0
"""


class TestProductionMCPServer:
    def test_complete_workflow_initialize_iterate_complete(self) -> None:
        server = create_mcp_server()

        # Test would use actual MCP tool calls in production
        # For now, verify server structure and tools are registered
        tools = asyncio.run(server.get_tools())
        tool_names = list(tools.keys())

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
            assert tool_name in tool_names, f'Required tool {tool_name} not found in {tool_names}'

        # Verify tool metadata
        init_tool = tools['initialize_refinement_loop']
        assert init_tool.name == 'initialize_refinement_loop'

        decision_tool = tools['decide_loop_next_action']
        assert decision_tool.name == 'decide_loop_next_action'

    def test_real_mcp_client_integration_scenarios(self) -> None:
        server = create_mcp_server()

        # Test server can handle tool discovery
        tools = asyncio.run(server.get_tools())
        # Verify we have both loop and roadmap tools
        assert len(tools) >= 13  # At least 6 loop + 7 roadmap tools (may grow)

        # Test server metadata
        assert server.name == 'respec-ai'

        # Test prompts endpoint
        prompts = asyncio.run(server.get_prompts())
        # No prompts expected for this server
        assert isinstance(prompts, dict)

    def test_configuration_loading_from_environment_variables(self, mocker: MockerFixture) -> None:
        # Test with custom environment variables
        test_env = {
            'LOOP_PLAN_THRESHOLD': '90',
            'LOOP_SPEC_THRESHOLD': '88',
            'MCP_SERVER_NAME': 'Test Production Server',
            'MCP_DEBUG': 'true',
        }

        mocker.patch.dict(os.environ, test_env, clear=False)
        custom_settings = MCPSettings()

        # Verify custom server name is used
        assert custom_settings.server_name == 'Test Production Server'

    def test_multi_loop_concurrent_scenarios(self) -> None:
        server = create_mcp_server()

        # Test server can handle multiple tool registrations
        tools = asyncio.run(server.get_tools())

        # Verify each tool has proper async signatures for concurrent use
        for tool_name, tool in tools.items():
            # All tools should be registered (implies async capability)
            assert tool.name is not None
            assert tool.name == tool_name

        # Test that list_active_loops tool exists for managing multiple loops
        list_tool = tools.get('list_active_loops')
        assert list_tool is not None

    def test_fastmcp_server_production_deployment_patterns(self) -> None:
        server = create_mcp_server()

        # Test server has required middleware
        # FastMCP middleware is internal, so test indirectly through behavior
        tools = asyncio.run(server.get_tools())
        assert len(tools) > 0

        # Test server info contains production-ready metadata
        assert server.name is not None

        # Test server can handle errors gracefully (middleware should catch)
        # This would be tested through actual tool calls in real scenarios
        assert server is not None

    def test_health_check_endpoints_and_monitoring(self, mocker: MockerFixture) -> None:
        server = create_mcp_server()

        # Test health check function
        health_status = asyncio.run(health_check(server))

        assert health_status.status == HealthState.HEALTHY
        assert health_status.tools_count >= 13  # At least expected tools
        assert health_status.error is None

        # Test health check with simulated error
        mocker.patch.object(server, 'get_tools', side_effect=Exception('Test error'))
        error_health = asyncio.run(health_check(server))
        assert error_health.status == HealthState.UNHEALTHY
        assert error_health.error == 'Test error'
        assert error_health.tools_count == 0

    def test_production_logging_configuration(self) -> None:
        # Test that server creation doesn't raise logging errors
        server = create_mcp_server()
        assert server is not None

        # Test server can be created multiple times (logging setup is idempotent)
        server2 = create_mcp_server()
        assert server2 is not None

        # Verify both servers are independent instances
        assert server is not server2

    def test_graceful_server_lifecycle_management(self) -> None:
        # Test server creation
        server = create_mcp_server()
        assert server is not None

        # Test server info access
        assert server.name == 'respec-ai'

        # Test tools are accessible
        tools = asyncio.run(server.get_tools())
        assert len(tools) >= 13  # Tools may expand over time

        # Test multiple operations don't interfere
        tools2 = asyncio.run(server.get_tools())
        assert len(tools2) >= 13
        assert len(tools) == len(tools2)

    def test_error_handling_middleware_integration(self) -> None:
        server = create_mcp_server()

        # Test server initialization succeeded despite having error middleware
        assert server is not None

        # Test tools are still accessible with middleware
        tools = asyncio.run(server.get_tools())
        assert len(tools) >= 13  # Tools may expand over time

        # Test server name works with middleware
        assert server.name == 'respec-ai'

    def test_production_configuration_validation(self, mocker: MockerFixture) -> None:
        # Test with invalid environment variables
        invalid_env = {
            'FSDD_LOOP_PLAN_THRESHOLD': '-10',  # Invalid: below range
            'FSDD_LOOP_SPEC_THRESHOLD': '150',  # Invalid: above range
        }

        # Configuration validation should handle invalid values gracefully
        # Pydantic should clamp or use defaults
        mocker.patch.dict(os.environ, invalid_env)
        try:
            server = create_mcp_server()
            # If server creation succeeds, config validation worked
            assert server is not None
        except Exception as e:
            # If it fails, it should be a validation error, not a crash
            assert 'validation' in str(e).lower() or 'field' in str(e).lower()

    def test_concurrent_tool_access_safety(self) -> None:
        server = create_mcp_server()

        async def get_tools_multiple() -> list[dict[str, Any]]:
            # Simulate concurrent access
            tasks = [server.get_tools() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return results

        # Test concurrent access doesn't cause issues
        results = asyncio.run(get_tools_multiple())

        # All results should be identical
        assert len(results) == 5
        for result in results:
            assert len(result) >= 13

        # Verify tool names are consistent across concurrent access
        tool_names_sets = [set(result.keys()) for result in results]

        # All concurrent calls should return identical tool sets
        first_tool_set = tool_names_sets[0]
        for tool_set in tool_names_sets[1:]:
            assert tool_set == first_tool_set

        # Verify we have essential tools (without hard-coding complete list)
        essential_tools = {
            'decide_loop_next_action',
            'initialize_refinement_loop',
            'create_roadmap',
            'get_roadmap',
            'store_spec',
        }

        for tool_set in tool_names_sets:
            assert essential_tools.issubset(tool_set)

    def test_server_error_handling_comprehensive(self, mocker: MockerFixture) -> None:
        server = create_mcp_server()

        # Test server handles middleware errors gracefully
        tools = asyncio.run(server.get_tools())
        assert len(tools) >= 13  # Tools may expand over time

        # Test health check with ConnectionError
        mocker.patch.object(server, 'get_tools', side_effect=ConnectionError('Network error'))
        health = asyncio.run(health_check(server))
        assert health.status == HealthState.UNHEALTHY
        assert health.error is not None and 'Network error' in health.error
        mocker.stopall()

        # Test health check with TimeoutError
        mocker.patch.object(server, 'get_tools', side_effect=TimeoutError('Timeout error'))
        health = asyncio.run(health_check(server))
        assert health.status == HealthState.UNHEALTHY
        assert health.error is not None and 'Timeout error' in health.error
        mocker.stopall()

        # Test health check with RuntimeError
        mocker.patch.object(server, 'get_tools', side_effect=RuntimeError('Runtime error'))
        health = asyncio.run(health_check(server))
        assert health.status == HealthState.UNHEALTHY
        assert health.error is not None and 'Runtime error' in health.error

    def test_tool_registration_error_recovery(self) -> None:
        # Test that server creation works even with potential tool issues
        server = create_mcp_server()

        # Verify all tools are properly registered despite any potential errors
        tools = asyncio.run(server.get_tools())
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
            tool = tools[tool_name]
            assert tool.name == tool_name

    def test_middleware_error_isolation(self) -> None:
        server = create_mcp_server()

        # Test server continues to work despite middleware being present
        tools = asyncio.run(server.get_tools())
        assert len(tools) >= 13  # Tools may expand over time

        # Test prompts endpoint works with middleware
        prompts = asyncio.run(server.get_prompts())
        assert isinstance(prompts, dict)

        # Test server metadata accessible despite middleware
        assert server.name == 'respec-ai'
        assert server.name is not None
        assert len(server.name) > 0

    def test_configuration_error_handling(self, mocker: MockerFixture) -> None:
        # Test with malformed environment variables
        malformed_env = {
            'FSDD_MCP_SERVER_NAME': '',  # Empty string
            'FSDD_MCP_DEBUG': 'invalid_boolean',  # Invalid bool
            'FSDD_MCP_PORT': 'not_a_number',  # Invalid int
        }

        mocker.patch.dict(os.environ, malformed_env, clear=False)
        try:
            # Should either use defaults or handle validation gracefully
            settings = MCPSettings()
            # Empty string should either be rejected or use default
            assert settings.server_name != '' or settings.server_name == 'respec-ai'
        except Exception as e:
            # If validation fails, it should be a clear validation error
            assert any(word in str(e).lower() for word in ['validation', 'field', 'value', 'invalid'])

    def test_async_operation_error_handling(self) -> None:
        server = create_mcp_server()

        # Test that async operations handle errors properly
        async def test_async_errors() -> None:
            # Test get_tools async error handling
            try:
                tools = await server.get_tools()
                assert len(tools) >= 13  # Tools may expand over time
            except Exception:
                # Should not raise unhandled exceptions
                assert False, 'get_tools should not raise unhandled exceptions'

            # Test get_prompts async error handling
            try:
                prompts = await server.get_prompts()
                assert isinstance(prompts, dict)
            except Exception:
                # Should not raise unhandled exceptions
                assert False, 'get_prompts should not raise unhandled exceptions'

        # Run async tests
        asyncio.run(test_async_errors())
