from abc import ABC, abstractmethod
from argparse import Namespace
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
    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def conversation_workflow_name(self) -> str: ...

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
    def add_mcp_permissions(self, project_path: Path) -> bool: ...

    @abstractmethod
    def is_mcp_registered(self, project_path: Path) -> bool: ...

    @abstractmethod
    def unregister_mcp_server(self, project_path: Path) -> bool: ...

    def unregister_all_mcp_servers(self, project_path: Path) -> int:
        removed = self.unregister_mcp_server(project_path)
        return 1 if removed else 0

    def post_init_setup(self, args: Namespace) -> int:
        return 0

    @abstractmethod
    def config_dir_name(self) -> str: ...

    @abstractmethod
    def plans_dir(self) -> str: ...

    @abstractmethod
    def render_agent_invocation(
        self,
        agent_name: str,
        description: str,
        params: list[tuple[str, str]],
    ) -> str: ...

    @abstractmethod
    def render_command_invocation(
        self,
        command_name: str,
        args_template: str,
        inline_guide: str,
        requires_user_interaction: bool = False,
    ) -> str: ...
