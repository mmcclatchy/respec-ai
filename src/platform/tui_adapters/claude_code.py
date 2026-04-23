from pathlib import Path

from src.cli.config.claude_config import (
    add_mcp_permissions as _add_mcp_permissions,
    is_mcp_server_registered,
    register_mcp_server as _register_mcp_server,
    unregister_all_respec_servers as _unregister_all_respec_servers,
    unregister_mcp_server as _unregister_mcp_server,
)
from src.platform.tool_enums import BuiltInToolCapability
from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter


class ClaudeCodeAdapter(TuiAdapter):
    @property
    def display_name(self) -> str:
        return 'Claude Code'

    @property
    def conversation_workflow_name(self) -> str:
        return 'the plan-conversation command'

    @property
    def ask_user_question_tool_name(self) -> str | None:
        return 'AskUserQuestion'

    @property
    def builtin_tool_name_map(self) -> dict[BuiltInToolCapability, str | None]:
        # Source of truth for Claude Code built-in tool runtime names.
        # Any new built-in capability must be reviewed here explicitly.
        return {
            BuiltInToolCapability.READ: 'Read',
            BuiltInToolCapability.WRITE: 'Write',
            BuiltInToolCapability.EDIT: 'Edit',
            BuiltInToolCapability.MULTI_EDIT: 'MultiEdit',
            BuiltInToolCapability.NOTEBOOK_EDIT: 'NotebookEdit',
            BuiltInToolCapability.GLOB: 'Glob',
            BuiltInToolCapability.GREP: 'Grep',
            BuiltInToolCapability.TASK: 'Task',
            BuiltInToolCapability.BASH: 'Bash',
            BuiltInToolCapability.BASH_OUTPUT: 'BashOutput',
            BuiltInToolCapability.KILL_SHELL: 'KillShell',
            BuiltInToolCapability.WEB_FETCH: 'WebFetch',
            BuiltInToolCapability.WEB_SEARCH: 'WebSearch',
            BuiltInToolCapability.TODO_WRITE: 'TodoWrite',
            BuiltInToolCapability.EXIT_PLAN_MODE: 'ExitPlanMode',
            BuiltInToolCapability.SLASH_COMMAND: 'SlashCommand',
            BuiltInToolCapability.ASK_USER_QUESTION: 'AskUserQuestion',
        }

    @property
    def selection_prompt_instruction(self) -> str:
        return 'Use AskUserQuestion tool to present options:'

    @property
    def selection_response_source(self) -> str:
        return 'AskUserQuestion response'

    def commands_dir(self, project_path: Path) -> Path:
        return project_path / '.claude' / 'commands'

    def prompts_dir(self, project_path: Path) -> Path:
        return project_path / '.claude' / 'agents'

    def render_agent(self, spec: AgentSpec) -> str:
        parts = [
            '---',
            f'name: {spec.name}',
            f'description: {spec.description}',
            f'model: {spec.model}',
        ]
        if spec.color:
            parts.append(f'color: {spec.color}')
        parts.append(f'tools: {", ".join(spec.tools)}')
        parts.append('---')
        return '\n'.join(parts) + '\n\n' + spec.body

    def render_command(self, spec: CommandSpec) -> str:
        parts = [
            '---',
            f'allowed-tools: {", ".join(spec.tools)}',
            f'argument-hint: {spec.argument_hint}',
            f'description: {spec.description}',
            '---',
        ]
        return '\n'.join(parts) + '\n\n' + spec.body

    def write_all(
        self,
        project_path: Path,
        agents: list[AgentSpec],
        commands: list[CommandSpec],
    ) -> list[Path]:
        commands_dir = self.commands_dir(project_path)
        agents_dir = self.prompts_dir(project_path)

        commands_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        for stale in commands_dir.glob('respec-*.md'):
            stale.unlink()
        for stale in agents_dir.glob('respec-*.md'):
            stale.unlink()

        files_written: list[Path] = []

        for cmd_spec in commands:
            content = self.render_command(cmd_spec)
            file_path = commands_dir / f'{cmd_spec.name}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(file_path)

        for agent_spec in agents:
            content = self.render_agent(agent_spec)
            file_path = agents_dir / f'{agent_spec.name}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(file_path)

        return files_written

    @property
    def reasoning_model(self) -> str:
        return 'opus'

    @property
    def orchestration_model(self) -> str:
        return 'sonnet'

    @property
    def coding_model(self) -> str:
        return 'sonnet'

    @property
    def review_model(self) -> str:
        return 'sonnet'

    def register_mcp_server(self, project_path: Path) -> bool:
        return _register_mcp_server(force=True)

    def add_mcp_permissions(self, project_path: Path) -> bool:
        return _add_mcp_permissions()

    def is_mcp_registered(self, project_path: Path) -> bool:
        return is_mcp_server_registered()

    def unregister_mcp_server(self, project_path: Path) -> bool:
        return _unregister_mcp_server()

    def unregister_all_mcp_servers(self, project_path: Path) -> int:
        return _unregister_all_respec_servers()

    def config_dir_name(self) -> str:
        return '.claude'

    def plans_dir(self) -> str:
        return '~/.claude/plans'

    def render_agent_invocation(
        self,
        agent_name: str,
        description: str,
        params: list[tuple[str, str]],
    ) -> str:
        lines = [f'Invoke: {agent_name}']
        if params:
            lines.append('Input:')
            for name, value in params:
                lines.append(f'  - {name}: {value}')
        return '\n'.join(lines)

    def render_command_invocation(
        self,
        command_name: str,
        args_template: str,
        inline_guide: str,
        requires_user_interaction: bool = False,
    ) -> str:
        return f'/{command_name} {args_template}'

    def render_command_reference(self, command_name: str) -> str:
        return f'/{command_name}'

    def render_parallel_fanout_policy(
        self,
        worker_group_label: str,
        completion_signal_label: str,
    ) -> str:
        if worker_group_label == 'create-phase agents':
            return (
                'IMPORTANT: Launch ALL create-phase workflows in a SINGLE message (parallel invocations).\n'
                'Do NOT launch agents sequentially. True parallelism requires one message with all invocations.\n\n'
                'Wait for all agents to complete before proceeding to result aggregation.'
            )
        if worker_group_label == 'Phase 1 review agents (excluding consolidator)':
            return ''
        return super().render_parallel_fanout_policy(worker_group_label, completion_signal_label)
