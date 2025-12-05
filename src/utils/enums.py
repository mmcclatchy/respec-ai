from enum import Enum

from src.utils.setting_configs import loop_config


class LoopType(Enum):
    PLAN = 'plan'
    ROADMAP = 'roadmap'
    SPEC = 'spec'
    BUILD_PLAN = 'build_plan'
    BUILD_CODE = 'build_code'
    ANALYST = 'analyst'

    @property
    def threshold(self) -> int:
        return getattr(loop_config, f'{self.value}_threshold')

    @property
    def improvement_threshold(self) -> int:
        return getattr(loop_config, f'{self.value}_improvement_threshold')

    @property
    def checkpoint_frequency(self) -> int:
        return getattr(loop_config, f'{self.value}_checkpoint_frequency')


class LoopStatus(Enum):
    INITIALIZED = 'initialized'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    USER_INPUT = 'user_input'
    REFINE = 'refine'


class OperationStatus(Enum):
    SUCCESS = 'success'
    ERROR = 'error'
    NOT_FOUND = 'not_found'


class HealthState(Enum):
    HEALTHY = 'healthy'
    UNHEALTHY = 'unhealthy'
