import json

import pytest
from src.utils.enums import HealthState, LoopStatus, LoopType, OperationStatus
from src.utils.setting_configs import loop_config


class TestOperationStatus:
    def test_operation_status_values(self) -> None:
        assert OperationStatus.SUCCESS.value == 'success'
        assert OperationStatus.ERROR.value == 'error'
        assert OperationStatus.NOT_FOUND.value == 'not_found'

    def test_operation_status_string_representation(self) -> None:
        assert str(OperationStatus.SUCCESS) == 'OperationStatus.SUCCESS'
        assert str(OperationStatus.ERROR) == 'OperationStatus.ERROR'
        assert str(OperationStatus.NOT_FOUND) == 'OperationStatus.NOT_FOUND'

    @pytest.mark.parametrize(
        'status,expected_value',
        [
            (OperationStatus.SUCCESS, 'success'),
            (OperationStatus.ERROR, 'error'),
            (OperationStatus.NOT_FOUND, 'not_found'),
        ],
    )
    def test_operation_status_value_consistency(self, status: OperationStatus, expected_value: str) -> None:
        assert status.value == expected_value


class TestLoopStatus:
    def test_loop_status_values(self) -> None:
        assert LoopStatus.INITIALIZED.value == 'initialized'
        assert LoopStatus.IN_PROGRESS.value == 'in_progress'
        assert LoopStatus.COMPLETED.value == 'completed'
        assert LoopStatus.USER_INPUT.value == 'user_input'
        assert LoopStatus.REFINE.value == 'refine'

    @pytest.mark.parametrize(
        'status,expected_value',
        [
            (LoopStatus.INITIALIZED, 'initialized'),
            (LoopStatus.IN_PROGRESS, 'in_progress'),
            (LoopStatus.COMPLETED, 'completed'),
            (LoopStatus.USER_INPUT, 'user_input'),
            (LoopStatus.REFINE, 'refine'),
        ],
    )
    def test_loop_status_value_consistency(self, status: LoopStatus, expected_value: str) -> None:
        assert status.value == expected_value


class TestLoopType:
    def test_loop_type_values(self) -> None:
        assert LoopType.PLAN.value == 'plan'
        assert LoopType.ROADMAP.value == 'roadmap'
        assert LoopType.SPEC.value == 'spec'
        assert LoopType.BUILD_PLAN.value == 'build_plan'
        assert LoopType.BUILD_CODE.value == 'build_code'
        assert LoopType.ANALYST.value == 'analyst'

    @pytest.mark.parametrize(
        'loop_type,config_suffix',
        [
            (LoopType.PLAN, 'plan'),
            (LoopType.ROADMAP, 'roadmap'),
            (LoopType.SPEC, 'spec'),
            (LoopType.BUILD_PLAN, 'build_plan'),
            (LoopType.BUILD_CODE, 'build_code'),
            (LoopType.ANALYST, 'analyst'),
        ],
    )
    def test_loop_type_threshold_property(self, loop_type: LoopType, config_suffix: str) -> None:
        expected_threshold = getattr(loop_config, f'{config_suffix}_threshold')

        assert loop_type.threshold == expected_threshold
        assert isinstance(loop_type.threshold, int)
        assert 1 <= loop_type.threshold <= 100

    @pytest.mark.parametrize(
        'loop_type,config_suffix',
        [
            (LoopType.PLAN, 'plan'),
            (LoopType.ROADMAP, 'roadmap'),
            (LoopType.SPEC, 'spec'),
            (LoopType.BUILD_PLAN, 'build_plan'),
            (LoopType.BUILD_CODE, 'build_code'),
            (LoopType.ANALYST, 'analyst'),
        ],
    )
    def test_loop_type_improvement_threshold_property(self, loop_type: LoopType, config_suffix: str) -> None:
        expected_improvement_threshold = getattr(loop_config, f'{config_suffix}_improvement_threshold')

        assert loop_type.improvement_threshold == expected_improvement_threshold
        assert isinstance(loop_type.improvement_threshold, int)
        assert 1 <= loop_type.improvement_threshold <= 100

    @pytest.mark.parametrize(
        'loop_type,config_suffix',
        [
            (LoopType.PLAN, 'plan'),
            (LoopType.ROADMAP, 'roadmap'),
            (LoopType.SPEC, 'spec'),
            (LoopType.BUILD_PLAN, 'build_plan'),
            (LoopType.BUILD_CODE, 'build_code'),
            (LoopType.ANALYST, 'analyst'),
        ],
    )
    def test_loop_type_checkpoint_frequency_property(self, loop_type: LoopType, config_suffix: str) -> None:
        expected_checkpoint_frequency = getattr(loop_config, f'{config_suffix}_checkpoint_frequency')

        assert loop_type.checkpoint_frequency == expected_checkpoint_frequency
        assert isinstance(loop_type.checkpoint_frequency, int)
        assert 1 <= loop_type.checkpoint_frequency <= 20

    def test_loop_type_property_integration(self) -> None:
        # Test build_code has highest threshold (95%)
        assert LoopType.BUILD_CODE.threshold == 95

        # Test analyst has highest improvement threshold (10%)
        assert LoopType.ANALYST.improvement_threshold == 10

        # Test all types have reasonable checkpoint frequencies
        for loop_type in LoopType:
            assert loop_type.checkpoint_frequency >= 3
            assert loop_type.checkpoint_frequency <= 5

    def test_loop_type_enum_creation_from_string(self) -> None:
        assert LoopType('plan') == LoopType.PLAN
        assert LoopType('spec') == LoopType.SPEC
        assert LoopType('build_code') == LoopType.BUILD_CODE

        with pytest.raises(ValueError):
            LoopType('invalid_loop_type')


class TestHealthState:
    def test_health_state_values(self) -> None:
        assert HealthState.HEALTHY.value == 'healthy'
        assert HealthState.UNHEALTHY.value == 'unhealthy'

    @pytest.mark.parametrize(
        'state,expected_value',
        [
            (HealthState.HEALTHY, 'healthy'),
            (HealthState.UNHEALTHY, 'unhealthy'),
        ],
    )
    def test_health_state_value_consistency(self, state: HealthState, expected_value: str) -> None:
        assert state.value == expected_value


class TestEnumInteroperability:
    def test_enums_are_distinct_types(self) -> None:
        # This should be caught at type-checking level, but verify runtime behavior
        operation_success = OperationStatus.SUCCESS
        loop_completed = LoopStatus.COMPLETED

        # They should be different types
        assert type(operation_success) is not type(loop_completed)
        assert operation_success != loop_completed

    def test_enum_serialization_behavior(self) -> None:
        # Test that enum values are JSON serializable

        status_value = OperationStatus.SUCCESS.value
        loop_value = LoopStatus.COMPLETED.value

        # Should be able to serialize the values
        serialized = json.dumps({'operation': status_value, 'loop': loop_value})

        assert 'success' in serialized
        assert 'completed' in serialized
