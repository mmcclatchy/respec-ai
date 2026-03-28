from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    model: str
    tools: list[str]
    body: str
    color: str | None
    is_orchestrator: bool


@dataclass(frozen=True)
class CommandSpec:
    name: str
    description: str
    argument_hint: str
    tools: list[str]
    body: str
    delegated_agents: list[str]
    model: str = 'sonnet'


class TuiAdapter(ABC):
    @abstractmethod
    def commands_dir(self, project_path: Path) -> Path: ...

    @abstractmethod
    def prompts_dir(self, project_path: Path) -> Path: ...

    @abstractmethod
    def render_agent(self, spec: AgentSpec) -> str: ...

    @abstractmethod
    def render_command(self, spec: CommandSpec) -> str: ...

    @abstractmethod
    def write_all(
        self,
        project_path: Path,
        agents: list[AgentSpec],
        commands: list[CommandSpec],
    ) -> list[Path]: ...

    @property
    @abstractmethod
    def reasoning_model(self) -> str: ...

    @property
    @abstractmethod
    def task_model(self) -> str: ...

    @abstractmethod
    def register_mcp_server(self, project_path: Path) -> bool: ...

    @abstractmethod
    def add_mcp_permissions(self) -> bool: ...

    @abstractmethod
    def is_mcp_registered(self, project_path: Path) -> bool: ...

    @abstractmethod
    def config_dir_name(self) -> str: ...

    @abstractmethod
    def plans_dir(self) -> str: ...
