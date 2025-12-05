import pytest
from src.mcp.tools.loop_tools import loop_tools
from src.utils.enums import LoopStatus
from src.utils.errors import LoopStateError, LoopValidationError
from src.utils.loop_state import MCPResponse


@pytest.fixture
def project_path() -> str:
    return '/tmp/test-project'


class TestLoopManagement:
    def test_initialize_refinement_loop_valid_inputs(self, project_path: str) -> None:
        result = loop_tools.initialize_refinement_loop(project_path, 'plan')

        assert isinstance(result, MCPResponse)
        assert result.status == LoopStatus.INITIALIZED
        assert isinstance(result.id, str)
        assert len(result.id) > 0

    def test_initialize_refinement_loop_invalid_loop_type(self, project_path: str) -> None:
        with pytest.raises(LoopValidationError):
            loop_tools.initialize_refinement_loop(project_path, 'invalid_type')

    def test_get_loop_status_existing_loop(self, project_path: str) -> None:
        init_result = loop_tools.initialize_refinement_loop(project_path, 'build_plan')
        loop_id = init_result.id

        status_result = loop_tools.get_loop_status(loop_id)

        assert isinstance(status_result, MCPResponse)
        assert status_result.id == loop_id
        assert status_result.status == LoopStatus.INITIALIZED

    def test_get_loop_status_nonexistent_loop(self) -> None:
        with pytest.raises(LoopStateError):
            loop_tools.get_loop_status('nonexistent-loop-id')

    def test_list_active_loops_empty_initially(self, project_path: str) -> None:
        result = loop_tools.list_active_loops(project_path)
        assert isinstance(result, list)

    def test_list_active_loops_with_loops(self, project_path: str) -> None:
        init1 = loop_tools.initialize_refinement_loop(project_path, 'plan')
        init2 = loop_tools.initialize_refinement_loop(project_path, 'spec')

        result = loop_tools.list_active_loops(project_path)

        assert isinstance(result, list)
        assert len(result) >= 2

        loop_ids = [loop.id for loop in result]
        assert init1.id in loop_ids
        assert init2.id in loop_ids

    def test_concurrent_loop_management(self, project_path: str) -> None:
        loop1 = loop_tools.initialize_refinement_loop(project_path, 'plan')
        loop2 = loop_tools.initialize_refinement_loop(project_path, 'spec')

        status1 = loop_tools.get_loop_status(loop1.id)
        status2 = loop_tools.get_loop_status(loop2.id)

        assert status1.id != status2.id
        assert status1.status == LoopStatus.INITIALIZED
        assert status2.status == LoopStatus.INITIALIZED

    def test_decide_loop_next_action_functionality(self, project_path: str) -> None:
        init_result = loop_tools.initialize_refinement_loop(project_path, 'build_code')
        loop_id = init_result.id

        # Test decision with high score (should complete)
        decision_result = loop_tools.decide_loop_next_action(loop_id, 95)

        assert isinstance(decision_result, MCPResponse)
        assert decision_result.id == loop_id

    def test_loop_id_generation_uniqueness(self, project_path: str) -> None:
        loop1 = loop_tools.initialize_refinement_loop(project_path, 'plan')
        loop2 = loop_tools.initialize_refinement_loop(project_path, 'plan')

        assert loop1.id != loop2.id
        assert isinstance(loop1.id, str)
        assert isinstance(loop2.id, str)
