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
    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def conversation_workflow_name(self) -> str: ...

    @property
    def ask_user_question_tool_name(self) -> str | None:
        """Return the adapter-specific interactive user prompt tool name.

        None means this adapter does not support an interactive prompt tool in
        generated command workflows.
        """
        return None

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
    def orchestration_model(self) -> str: ...

    @property
    @abstractmethod
    def coding_model(self) -> str: ...

    @property
    @abstractmethod
    def review_model(self) -> str: ...

    @property
    def task_model(self) -> str:
        return self.orchestration_model

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

    @abstractmethod
    def config_dir_name(self) -> str: ...

    @abstractmethod
    def plans_dir(self) -> str: ...

    @property
    @abstractmethod
    def loop_commit_instructions(self) -> str: ...

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

    @abstractmethod
    def render_command_reference(self, command_name: str) -> str: ...

    def parallel_worker_limit(self) -> int:
        """Return max active workers hint for adapter-specific orchestration guidance.

        Default `0` means no adapter-specific cap guidance.
        """
        return 0

    def render_parallel_fanout_policy(
        self,
        worker_group_label: str,
        completion_signal_label: str,
    ) -> str:
        return (
            f'Launch all {worker_group_label} in parallel.\n'
            f'Wait for all {worker_group_label} to complete before proceeding.\n'
            f'Collect {completion_signal_label} for each item before aggregation.'
        )

    def count_generated_commands(self, project_path: Path) -> int:
        commands_dir = self.commands_dir(project_path)
        if not commands_dir.exists():
            return 0
        return len(list(commands_dir.glob('*.md')))

    def count_generated_agents(self, project_path: Path) -> int:
        prompts_dir = self.prompts_dir(project_path)
        if not prompts_dir.exists():
            return 0
        return len(list(prompts_dir.glob('*.md')))
