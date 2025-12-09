import time

import pytest
from src.mcp.tools.loop_tools import loop_tools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse


@pytest.fixture
def project_name() -> str:
    return 'test-project'


async def add_feedback_and_decide(loop_id: str, score: int, iteration: int, agent: CriticAgent) -> MCPResponse:
    state_manager = loop_tools.state
    loop_state = await state_manager.get_loop(loop_id)
    feedback = CriticFeedback(
        loop_id=loop_id,
        critic_agent=agent,
        iteration=iteration,
        overall_score=score,
        assessment_summary=f'Assessment {iteration}',
        detailed_feedback=f'Details for iteration {iteration}',
        key_issues=[],
        recommendations=[],
    )
    loop_state.add_feedback(feedback)
    return await loop_tools.decide_loop_next_action(loop_id)


class TestLoopPerformance:
    @pytest.mark.asyncio
    async def test_decision_engine_performance_with_large_iteration_counts(self, project_name: str) -> None:
        loop_id = (await loop_tools.initialize_refinement_loop(project_name, 'plan')).id

        start_time = time.perf_counter()

        # Simulate 50 iterations with varying scores
        for i in range(50):
            score = 60 + (i % 10)  # Scores between 60-69 to avoid completion
            result = await add_feedback_and_decide(loop_id, score, i + 1, CriticAgent.PLAN_CRITIC)
            assert isinstance(result, MCPResponse)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Performance requirement: should complete 50 iterations in under 1 second
        assert execution_time < 1.0, f'Large iteration test took {execution_time:.3f}s, expected < 1.0s'

        # Additional verification: ensure we're actually doing work (very fast is okay)
        assert execution_time > 0.0001, (
            f'Test completed too quickly ({execution_time:.6f}s), may not be measuring correctly'
        )

    @pytest.mark.asyncio
    async def test_configuration_loading_performance(self, project_name: str) -> None:
        start_time = time.perf_counter()

        # Create multiple loops to test configuration access
        loops = []
        for _ in range(20):
            for loop_type in ['plan', 'spec', 'build_plan', 'build_code']:
                loop = await loop_tools.initialize_refinement_loop(project_name, loop_type)
                loops.append(loop)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Performance requirement: creating 80 loops should take under 0.5 seconds
        assert execution_time < 0.5, f'Configuration loading test took {execution_time:.3f}s, expected < 0.5s'
        assert len(loops) == 80

    @pytest.mark.asyncio
    async def test_memory_usage_patterns_during_long_loops(self, project_name: str) -> None:
        loop_id = (await loop_tools.initialize_refinement_loop(project_name, 'spec')).id

        # Track loop operations without completion
        initial_active_loops = len(await loop_tools.list_active_loops(project_name))

        # Run 100 score decisions on same loop
        for i in range(100):
            score = 70 + (i % 5)  # Scores 70-74 to stay below threshold
            result = await add_feedback_and_decide(loop_id, score, i + 1, CriticAgent.SPEC_CRITIC)
            assert result.status in [LoopStatus.REFINE, LoopStatus.USER_INPUT]

        # Verify memory doesn't grow unbounded
        final_active_loops = len(await loop_tools.list_active_loops(project_name))

        # Should not create additional loops
        assert final_active_loops == initial_active_loops

        # Verify loop still functions correctly
        status = await loop_tools.get_loop_status(loop_id)
        assert status.id == loop_id

    @pytest.mark.asyncio
    async def test_concurrent_access_performance(self, project_name: str) -> None:
        # Create multiple loops for concurrent access
        loops = []
        for i in range(10):
            loop = await loop_tools.initialize_refinement_loop(project_name, 'plan')
            loops.append(loop)

        start_time = time.perf_counter()

        # Simulate concurrent operations on different loops
        for iteration in range(5):
            for i, loop in enumerate(loops):
                score = 60 + (iteration * 2) + (i % 3)
                result = await add_feedback_and_decide(loop.id, score, iteration + 1, CriticAgent.PLAN_CRITIC)
                assert isinstance(result, MCPResponse)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Performance requirement: 50 operations across 10 loops in under 0.5 seconds
        assert execution_time < 0.5, f'Concurrent access test took {execution_time:.3f}s, expected < 0.5s'

    @pytest.mark.asyncio
    async def test_stagnation_detection_performance(self, project_name: str) -> None:
        loop_id = (await loop_tools.initialize_refinement_loop(project_name, 'build_plan')).id

        start_time = time.perf_counter()

        # Create stagnation pattern repeatedly
        stagnation_scores = [70, 71, 70, 71, 70]
        iteration = 1
        for _ in range(10):
            for score in stagnation_scores:
                result = await add_feedback_and_decide(loop_id, score, iteration, CriticAgent.BUILD_CRITIC)
                iteration += 1
                if result.status == LoopStatus.USER_INPUT:
                    break

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Performance requirement: stagnation detection should be fast
        assert execution_time < 0.1, f'Stagnation detection took {execution_time:.3f}s, expected < 0.1s'

    @pytest.mark.asyncio
    async def test_score_history_memory_efficiency(self, project_name: str) -> None:
        loop_id = (await loop_tools.initialize_refinement_loop(project_name, 'spec')).id

        # Add many scores to test memory usage
        for i in range(200):
            score = 70 + (i % 10)  # Vary scores to avoid early completion
            try:
                result = await add_feedback_and_decide(loop_id, score, i + 1, CriticAgent.SPEC_CRITIC)
                # Break if loop completes or requests user input
                if result.status in [LoopStatus.COMPLETED, LoopStatus.USER_INPUT]:
                    break
            except Exception:
                # If we hit memory or performance issues, that's a failure
                pytest.fail(f'Loop failed after {i} iterations')

        # Verify loop still responds correctly
        status = await loop_tools.get_loop_status(loop_id)
        assert status.id == loop_id

    @pytest.mark.asyncio
    async def test_loop_management_scalability(self, project_name: str) -> None:
        start_time = time.perf_counter()

        # Create many loops
        created_loops = []
        for i in range(50):
            loop_type = ['plan', 'spec', 'build_plan', 'build_code'][i % 4]
            loop = await loop_tools.initialize_refinement_loop(project_name, loop_type)
            created_loops.append(loop)

        # Test list_active_loops performance
        list_start = time.perf_counter()
        active_loops = await loop_tools.list_active_loops(project_name)
        list_end = time.perf_counter()

        # Test individual loop status retrieval
        status_start = time.perf_counter()
        for loop in created_loops[-10:]:  # Test last 10 (which should still be in memory)
            status = await loop_tools.get_loop_status(loop.id)
            assert status.id == loop.id
        status_end = time.perf_counter()

        end_time = time.perf_counter()

        total_time = end_time - start_time
        list_time = list_end - list_start
        status_time = status_end - status_start

        # Performance requirements
        assert total_time < 2.0, f'Total scalability test took {total_time:.3f}s, expected < 2.0s'
        assert list_time < 0.1, f'List active loops took {list_time:.3f}s, expected < 0.1s'
        assert status_time < 0.1, f'Status retrieval took {status_time:.3f}s, expected < 0.1s'
        assert (
            len(active_loops) <= 10
        )  # Limited by default history size, but should handle large number of creations efficiently

    @pytest.mark.asyncio
    async def test_repeated_operations_performance_consistency(self, project_name: str) -> None:
        loop_id = (await loop_tools.initialize_refinement_loop(project_name, 'plan')).id

        times: list[float] = []

        # Measure performance of repeated operations
        for i in range(20):
            start = time.perf_counter()

            # Perform standardized operation
            result = await add_feedback_and_decide(loop_id, 70 + (i % 5), i + 1, CriticAgent.PLAN_CRITIC)
            await loop_tools.get_loop_status(loop_id)

            end = time.perf_counter()
            times.append(end - start)

            # Stop if loop completes or needs user input
            if result.status in [LoopStatus.COMPLETED, LoopStatus.USER_INPUT]:
                break

        # Performance consistency requirements
        avg_time = sum(times) / len(times)
        max_time = max(times)

        assert avg_time < 0.01, f'Average operation time {avg_time:.4f}s, expected < 0.01s'
        assert max_time < 0.05, f'Max operation time {max_time:.4f}s, expected < 0.05s'

        # Verify no significant performance degradation
        if len(times) >= 10:
            first_half_avg = sum(times[: len(times) // 2]) / (len(times) // 2)
            second_half_avg = sum(times[len(times) // 2 :]) / (len(times) - len(times) // 2)

            # Second half should not be more than 2x slower than first half
            degradation_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1
            assert degradation_ratio < 2.0, f'Performance degraded by {degradation_ratio:.2f}x'
