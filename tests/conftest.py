import logging
from typing import Generator
from unittest.mock import patch

import pytest

from services.mcp.tools.loop_tools import LoopTools
from services.mcp.tools.roadmap_tools import RoadmapTools
from services.utils.state_manager import InMemoryStateManager


def pytest_configure(config: pytest.Config) -> None:
    logging.getLogger('state_manager').setLevel(logging.WARNING)


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
