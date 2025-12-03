import logging
from typing import Generator
from unittest.mock import patch

import pytest

from services.mcp.tools.loop_tools import LoopTools
from services.mcp.tools.roadmap_tools import RoadmapTools
from services.utils.state_manager import InMemoryStateManager
from services.utils.setting_configs import LoopConfig


def pytest_configure(config: pytest.Config) -> None:
    logging.getLogger('state_manager').setLevel(logging.WARNING)
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('mcp').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.WARNING)


# No longer need to mock the entire MCP server module since we removed fake markdown tools


@pytest.fixture
def isolated_state_manager() -> InMemoryStateManager:
    return InMemoryStateManager()


@pytest.fixture
def isolated_roadmap_tools(isolated_state_manager: InMemoryStateManager) -> RoadmapTools:
    return RoadmapTools(isolated_state_manager)


@pytest.fixture
def isolated_loop_tools(isolated_state_manager: InMemoryStateManager) -> LoopTools:
    return LoopTools(isolated_state_manager)


@pytest.fixture(autouse=True)
def mock_shared_state(isolated_state_manager: InMemoryStateManager) -> Generator[InMemoryStateManager, None, None]:
    with patch('services.shared.state_manager', isolated_state_manager):
        # Also patch the imported instances in the tool modules
        with patch('services.mcp.tools.roadmap_tools.state_manager', isolated_state_manager):
            with patch('services.mcp.tools.loop_tools.state_manager', isolated_state_manager):
                yield isolated_state_manager


@pytest.fixture(autouse=True)
def stable_loop_config() -> Generator[LoopConfig, None, None]:
    """Provide consistent loop configuration for all tests.

    This fixture ensures tests use known, stable threshold values regardless of
    environment variables or default changes.
    """
    test_config = LoopConfig(
        # Thresholds for loop completion
        plan_threshold=90,
        analyst_threshold=90,
        roadmap_threshold=90,
        spec_threshold=90,
        build_plan_threshold=90,
        build_code_threshold=95,
        # Improvement thresholds for stagnation detection
        plan_improvement_threshold=5,
        analyst_improvement_threshold=10,
        roadmap_improvement_threshold=10,
        spec_improvement_threshold=5,
        build_plan_improvement_threshold=5,
        build_code_improvement_threshold=5,
        # Checkpoint frequencies for user input triggers
        plan_checkpoint_frequency=5,
        analyst_checkpoint_frequency=3,
        roadmap_checkpoint_frequency=5,
        spec_checkpoint_frequency=5,
        build_plan_checkpoint_frequency=5,
        build_code_checkpoint_frequency=5,
    )

    with patch('services.utils.setting_configs.loop_config', test_config):
        with patch('services.utils.enums.loop_config', test_config):
            yield test_config
