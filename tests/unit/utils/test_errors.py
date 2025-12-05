import pytest
from fastmcp.exceptions import ToolError
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopError,
    LoopInvalidError,
    LoopNotFoundError,
    LoopStateError,
    LoopValidationError,
    RoadmapError,
    RoadmapNotFoundError,
    RoadmapValidationError,
    SpecNotFoundError,
)


class TestLoopErrors:
    def test_loop_error_base_class(self) -> None:
        error = LoopError('Test error')

        assert isinstance(error, Exception)
        assert str(error) == 'Test error'

    def test_loop_not_found_error_inheritance(self) -> None:
        error = LoopNotFoundError('Loop not found')

        assert isinstance(error, LoopError)
        assert isinstance(error, Exception)
        assert str(error) == 'Loop not found'

    def test_loop_already_exists_error_inheritance(self) -> None:
        error = LoopAlreadyExistsError('Loop exists')

        assert isinstance(error, LoopError)
        assert isinstance(error, Exception)
        assert str(error) == 'Loop exists'

    def test_loop_invalid_error_inheritance(self) -> None:
        error = LoopInvalidError('Invalid loop')

        assert isinstance(error, LoopError)
        assert isinstance(error, Exception)
        assert str(error) == 'Invalid loop'


class TestLoopValidationError:
    def test_loop_validation_error_inheritance(self) -> None:
        error = LoopValidationError('score', 'Must be between 0 and 100')

        assert isinstance(error, ToolError)
        assert isinstance(error, Exception)

    def test_loop_validation_error_message_format(self) -> None:
        error = LoopValidationError('loop_type', 'Must be one of valid types')

        expected_message = 'Invalid loop_type: Must be one of valid types'
        assert str(error) == expected_message

    def test_loop_validation_error_field_access(self) -> None:
        error = LoopValidationError('current_score', 'Score out of range')

        assert error.field == 'current_score'
        assert 'current_score' in str(error)

    @pytest.mark.parametrize(
        'field,message,expected_format',
        [
            ('score', 'Invalid range', 'Invalid score: Invalid range'),
            ('loop_id', 'Not found', 'Invalid loop_id: Not found'),
            ('iteration', 'Below minimum', 'Invalid iteration: Below minimum'),
        ],
    )
    def test_loop_validation_error_message_consistency(self, field: str, message: str, expected_format: str) -> None:
        error = LoopValidationError(field, message)

        assert str(error) == expected_format
        assert error.field == field


class TestLoopStateError:
    def test_loop_state_error_inheritance(self) -> None:
        error = LoopStateError('loop-123', 'status_check', 'Internal error')

        assert isinstance(error, ToolError)
        assert isinstance(error, Exception)

    def test_loop_state_error_message_format(self) -> None:
        error = LoopStateError('loop-456', 'decision', 'Stagnation detected')

        expected_message = 'Loop decision failed for loop-456: Stagnation detected'
        assert str(error) == expected_message

    def test_loop_state_error_loop_id_access(self) -> None:
        error = LoopStateError('test-loop', 'initialization', 'Database error')

        assert error.loop_id == 'test-loop'
        assert 'test-loop' in str(error)

    @pytest.mark.parametrize(
        'loop_id,operation,details,expected_substring',
        [
            ('loop-1', 'creation', 'Memory full', 'Loop creation failed for loop-1'),
            ('user-loop', 'update', 'Invalid state', 'Loop update failed for user-loop'),
            ('temp-123', 'deletion', 'Not authorized', 'Loop deletion failed for temp-123'),
        ],
    )
    def test_loop_state_error_message_consistency(
        self, loop_id: str, operation: str, details: str, expected_substring: str
    ) -> None:
        error = LoopStateError(loop_id, operation, details)

        assert expected_substring in str(error)
        assert details in str(error)
        assert error.loop_id == loop_id


class TestRoadmapErrors:
    def test_roadmap_error_base_class(self) -> None:
        error = RoadmapError('Roadmap error')

        assert isinstance(error, Exception)
        assert str(error) == 'Roadmap error'

    def test_roadmap_not_found_error_inheritance(self) -> None:
        error = RoadmapNotFoundError('Roadmap not found')

        assert isinstance(error, RoadmapError)
        assert isinstance(error, Exception)
        assert str(error) == 'Roadmap not found'

    def test_spec_not_found_error_inheritance(self) -> None:
        error = SpecNotFoundError('Spec not found')

        assert isinstance(error, RoadmapError)
        assert isinstance(error, Exception)
        assert str(error) == 'Spec not found'


class TestRoadmapValidationError:
    def test_roadmap_validation_error_inheritance(self) -> None:
        error = RoadmapValidationError('project_name', 'Cannot be empty')

        assert isinstance(error, ToolError)
        assert isinstance(error, Exception)

    def test_roadmap_validation_error_message_format(self) -> None:
        error = RoadmapValidationError('spec_name', 'Must be unique')

        expected_message = 'Invalid spec_name: Must be unique'
        assert str(error) == expected_message

    def test_roadmap_validation_error_field_access(self) -> None:
        error = RoadmapValidationError('markdown', 'Invalid format')

        assert error.field == 'markdown'
        assert 'markdown' in str(error)

    @pytest.mark.parametrize(
        'field,message,expected_format',
        [
            ('project_name', 'Too long', 'Invalid project_name: Too long'),
            ('roadmap_name', 'Contains invalid chars', 'Invalid roadmap_name: Contains invalid chars'),
            ('spec_content', 'Empty content', 'Invalid spec_content: Empty content'),
        ],
    )
    def test_roadmap_validation_error_message_consistency(self, field: str, message: str, expected_format: str) -> None:
        error = RoadmapValidationError(field, message)

        assert str(error) == expected_format
        assert error.field == field


class TestErrorInteroperability:
    def test_tool_errors_are_mcp_compatible(self) -> None:
        validation_error = LoopValidationError('test', 'test message')
        state_error = LoopStateError('loop-1', 'test', 'test details')
        roadmap_error = RoadmapValidationError('field', 'test message')

        # All should be ToolError instances
        assert isinstance(validation_error, ToolError)
        assert isinstance(state_error, ToolError)
        assert isinstance(roadmap_error, ToolError)

    def test_domain_errors_are_separate_hierarchies(self) -> None:
        loop_error = LoopNotFoundError('Loop not found')
        roadmap_error = RoadmapNotFoundError('Roadmap not found')

        # Should not be instances of each other's base classes
        assert not isinstance(loop_error, RoadmapError)
        assert not isinstance(roadmap_error, LoopError)

        # But both should be Exceptions
        assert isinstance(loop_error, Exception)
        assert isinstance(roadmap_error, Exception)

    def test_error_message_uniqueness(self) -> None:
        validation_msg = str(LoopValidationError('field', 'message'))
        state_msg = str(LoopStateError('loop', 'op', 'message'))
        roadmap_msg = str(RoadmapValidationError('field', 'message'))

        # Should be able to distinguish error types by message content
        assert 'Invalid field' in validation_msg
        assert 'failed for loop' in state_msg
        assert 'Invalid field' in roadmap_msg

        # Validation errors should be distinguishable by context or type
        # Both have same format but come from different error classes
        loop_validation = LoopValidationError('field', 'message')
        roadmap_validation = RoadmapValidationError('field', 'message')
        assert type(loop_validation) is not type(roadmap_validation)

    def test_exception_chaining_behavior(self) -> None:
        try:
            try:
                raise ValueError('Original error')
            except ValueError as e:
                raise LoopStateError('loop-1', 'test', 'Chained error') from e
        except LoopStateError as final_error:
            assert final_error.__cause__ is not None
            assert isinstance(final_error.__cause__, ValueError)
            assert 'Original error' in str(final_error.__cause__)
