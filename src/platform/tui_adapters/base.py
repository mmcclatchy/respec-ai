from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..tool_enums import BuiltInToolCapability


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
        return self.render_builtin_tool_name(BuiltInToolCapability.ASK_USER_QUESTION)

    @property
    @abstractmethod
    def builtin_tool_name_map(self) -> dict[BuiltInToolCapability, str | None]:
        """Map each built-in capability to a real runtime tool name or explicit non-support.

        NOTE FOR MAINTAINERS:
        Runtime tool names are adapter-specific. Every concrete adapter MUST
        make an explicit decision for every capability in
        `BuiltInToolCapability`, even if that decision is `None` for
        unsupported tools. Adding a new built-in capability requires updating
        all adapters before shared code may use it.
        """
        ...

    def render_builtin_tool_name(self, capability: BuiltInToolCapability) -> str | None:
        return self.builtin_tool_name_map[capability]

    @property
    def selection_prompt_instruction(self) -> str:
        ask_tool = self.ask_user_question_tool_name
        if ask_tool:
            return f'Use {ask_tool} tool to present options:'
        return 'Ask the user directly with a numbered options list and require a single explicit selection before continuing:'

    @property
    def selection_response_source(self) -> str:
        ask_tool = self.ask_user_question_tool_name
        return f'{ask_tool} response' if ask_tool else 'the user response'

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
