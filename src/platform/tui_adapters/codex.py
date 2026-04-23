import shutil
from pathlib import Path

from src.cli.config.global_config import load_global_models
from src.platform.tool_enums import BuiltInToolCapability
from src.cli.config.codex_config import (
    is_mcp_server_registered,
    load_codex_config,
    register_mcp_server as _register_mcp_server,
    unregister_all_respec_servers as _unregister_all_respec_servers,
    unregister_mcp_server as _unregister_mcp_server,
)
from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter


_PRIMARY_COMMAND_SKILLS = {'respec-plan', 'respec-phase', 'respec-code', 'respec-patch'}
_PREFLIGHT_COMMAND_SKILLS = {'respec-standards'}
_SECONDARY_COMMAND_PARENTS = {
    'respec-roadmap': 'respec-plan',
    'respec-task': 'respec-phase',
}
_INTERNAL_COMMAND_SKILLS = {'respec-plan-conversation'}


class CodexAdapter(TuiAdapter):
    @property
    def display_name(self) -> str:
        return 'OpenAI Codex'

    @property
    def conversation_workflow_name(self) -> str:
        return 'the conversation workflow'

    @property
    def builtin_tool_name_map(self) -> dict[BuiltInToolCapability, str | None]:
        # Source of truth for Codex built-in tool spellings emitted by this repo.
        # Any new built-in capability must be reviewed here explicitly. Preserve
        # existing non-question spellings unless separately verified.
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
            BuiltInToolCapability.ASK_USER_QUESTION: None,
        }

    @property
    def selection_prompt_instruction(self) -> str:
        return (
            'Present these options directly to the user in the chat UI as a numbered list. '
            'This is a user-facing prompt, not an internal instruction. '
            'Require a single explicit selection before continuing:'
        )

    @property
    def selection_response_source(self) -> str:
        return 'the user response'

    def commands_dir(self, project_path: Path) -> Path:
        return project_path / '.codex' / 'commands'

    def prompts_dir(self, project_path: Path) -> Path:
        return project_path / '.codex' / 'agents'

    def skills_dir(self, project_path: Path) -> Path:
        return project_path / '.codex' / 'skills'

    def render_agent(self, spec: AgentSpec) -> str:
        parts = [
            '---',
            f'name: {spec.name}',
            f'description: {spec.description}',
            f'model: {spec.model}',
            f'tools: {", ".join(spec.tools)}',
            '---',
        ]
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
        skills_dir = self.skills_dir(project_path)
        commands_dir = self.commands_dir(project_path)
        agents_dir = self.prompts_dir(project_path)

        skills_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        if commands_dir.exists():
            for stale in commands_dir.glob('respec-*.md'):
                stale.unlink()
        if agents_dir.exists():
            for stale in agents_dir.glob('respec-*.md'):
                stale.unlink()
            for stale in agents_dir.glob('respec-*.toml'):
                stale.unlink()
        for stale in skills_dir.glob('respec-*'):
            if stale.is_dir():
                shutil.rmtree(stale)
            elif stale.is_file():
                stale.unlink()

        files_written: list[Path] = []

        for cmd_spec in commands:
            command_description = self._command_short_description(cmd_spec.name, cmd_spec.description)
            skill_dir = skills_dir / cmd_spec.name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / 'SKILL.md'
            skill_path.write_text(self._render_command_skill(cmd_spec, command_description), encoding='utf-8')
            files_written.append(skill_path)
            openai_yaml_path = skill_dir / 'agents' / 'openai.yaml'
            openai_yaml_path.parent.mkdir(parents=True, exist_ok=True)
            openai_yaml_path.write_text(
                self._render_openai_yaml(
                    display_name=self._command_display_name(cmd_spec.name),
                    short_description=command_description,
                    default_prompt=self._command_default_prompt(cmd_spec.name, cmd_spec.argument_hint),
                    allow_implicit_invocation=self._allow_implicit_command_invocation(cmd_spec.name),
                ),
                encoding='utf-8',
            )
            files_written.append(openai_yaml_path)

        for agent_spec in agents:
            agent_runtime_name = self._agent_runtime_name(agent_spec.name)
            agent_path = agents_dir / f'{agent_runtime_name}.toml'
            agent_path.write_text(
                self._render_agent_toml(agent_spec, agent_runtime_name),
                encoding='utf-8',
            )
            files_written.append(agent_path)

        return files_written

    @property
    def reasoning_model(self) -> str:
        models = load_global_models('codex')
        if 'reasoning' not in models:
            raise RuntimeError("Codex reasoning model not configured. Run 'respec-ai models codex' first.")
        return models['reasoning']

    @property
    def orchestration_model(self) -> str:
        models = load_global_models('codex')
        if 'orchestration' not in models and 'task' not in models:
            raise RuntimeError("Codex orchestration model not configured. Run 'respec-ai models codex' first.")
        orchestration = models.get('orchestration')
        if orchestration:
            return orchestration
        return models['task']

    @property
    def coding_model(self) -> str:
        models = load_global_models('codex')
        if 'coding' not in models and 'task' not in models:
            raise RuntimeError("Codex coding model not configured. Run 'respec-ai models codex' first.")
        coding = models.get('coding')
        if coding:
            return coding
        orchestration = models.get('orchestration')
        if orchestration:
            return orchestration
        return models['task']

    @property
    def review_model(self) -> str:
        models = load_global_models('codex')
        if 'review' not in models and 'task' not in models:
            raise RuntimeError("Codex review model not configured. Run 'respec-ai models codex' first.")
        review = models.get('review')
        if review:
            return review
        orchestration = models.get('orchestration')
        if orchestration:
            return orchestration
        return models['task']

    def register_mcp_server(self, project_path: Path) -> bool:
        return _register_mcp_server(force=True)

    def add_mcp_permissions(self, project_path: Path) -> bool:
        return True

    def is_mcp_registered(self, project_path: Path) -> bool:
        return is_mcp_server_registered()

    def unregister_mcp_server(self, project_path: Path) -> bool:
        return _unregister_mcp_server()

    def unregister_all_mcp_servers(self, project_path: Path) -> int:
        return _unregister_all_respec_servers()

    def config_dir_name(self) -> str:
        return '.codex'

    def plans_dir(self) -> str:
        return '.codex/plans'

    def render_agent_invocation(
        self,
        agent_name: str,
        description: str,
        params: list[tuple[str, str]],
    ) -> str:
        agent_runtime_name = self._agent_runtime_name(agent_name)
        lines = [f'Invoke the `{agent_runtime_name}` agent to {description}.']
        if params:
            lines.append('Input:')
            for name, value in params:
                lines.append(f'  - {name}: {value}')
        lines.append('When using a full-history or forked-context spawn, pass only the message plus the listed inputs.')
        lines.append(
            'Use the rendered runtime agent name exactly. Omit agent_type, model, and reasoning_effort because Codex inherits them from the parent context.'
        )
        lines.append('Wait for completion, harvest output, then close the completed agent before continuing.')
        return '\n'.join(lines)

    def render_command_invocation(
        self,
        command_name: str,
        args_template: str,
        inline_guide: str,
        requires_user_interaction: bool = False,
    ) -> str:
        if requires_user_interaction:
            return inline_guide
        return f'Invoke the `{command_name}` skill with: `{args_template}`.'

    def render_command_reference(self, command_name: str) -> str:
        return f'`{command_name}` skill'

    def parallel_worker_limit(self) -> int:
        default_limit = 6
        try:
            config = load_codex_config()
        except Exception:
            return default_limit

        agents_config = config.get('agents')
        if not isinstance(agents_config, dict):
            return default_limit

        limit = agents_config.get('max_threads')
        if isinstance(limit, int) and limit > 0:
            return limit
        return default_limit

    def render_parallel_fanout_policy(
        self,
        worker_group_label: str,
        completion_signal_label: str,
    ) -> str:
        bounded_policy = self._render_bounded_parallel_policy(worker_group_label, completion_signal_label)
        if worker_group_label == 'Phase 1 review agents (excluding consolidator)':
            return f'\n\n{bounded_policy}\n\n'
        return bounded_policy

    def _render_bounded_parallel_policy(
        self,
        worker_group_label: str,
        completion_signal_label: str,
    ) -> str:
        max_workers = self.parallel_worker_limit()
        return (
            f'Use bounded parallel execution for {worker_group_label}.\n'
            f'MAX_ACTIVE_WORKERS = {max_workers}\n'
            '\n'
            'Initialize:\n'
            f'- PENDING_ITEMS: all {worker_group_label} not started yet\n'
            '- ACTIVE_WORKERS: currently running workers\n'
            '- SUCCEEDED_ITEMS / FAILED_ITEMS trackers\n'
            '\n'
            'Execution loop:\n'
            '1. While PENDING_ITEMS is not empty AND len(ACTIVE_WORKERS) < MAX_ACTIVE_WORKERS:\n'
            '   - Spawn one worker for the next pending item.\n'
            '   - If spawn succeeds, add worker handle to ACTIVE_WORKERS.\n'
            '   - If spawn fails:\n'
            '     - If ACTIVE_WORKERS is non-empty: wait for one active worker to complete, harvest output, close it, '
            'remove it from ACTIVE_WORKERS, then retry spawning.\n'
            '     - If ACTIVE_WORKERS is empty: record this item in FAILED_ITEMS with diagnostics and continue.\n'
            '2. If ACTIVE_WORKERS is non-empty, wait for one completion, harvest output, close the completed worker, '
            'remove it from ACTIVE_WORKERS, and continue.\n'
            '\n'
            f'Continue until both PENDING_ITEMS and ACTIVE_WORKERS are empty, then validate {completion_signal_label}. '
            'Do not proceed with dangling completed workers left open.'
        )

    def count_generated_commands(self, project_path: Path) -> int:
        skills_dir = self.skills_dir(project_path)
        if not skills_dir.exists():
            return 0
        return sum(
            1
            for skill_dir in skills_dir.iterdir()
            if skill_dir.is_dir()
            and (skill_dir / 'SKILL.md').exists()
            and skill_dir.name.startswith('respec-')
            and not skill_dir.name.endswith('-agent')
        )

    def count_generated_agents(self, project_path: Path) -> int:
        agents_dir = self.prompts_dir(project_path)
        if not agents_dir.exists():
            return 0
        return sum(1 for agent_file in agents_dir.glob('respec-*-agent.toml') if agent_file.is_file())

    def _render_command_skill(self, spec: CommandSpec, command_description: str) -> str:
        usage_hint = self._command_usage_hint(spec.name, spec.argument_hint)
        usage_line = f'Usage: {usage_hint}\n' if usage_hint else ''
        return (
            '---\n'
            f'name: {spec.name}\n'
            f'description: {command_description}\n'
            '---\n\n'
            f'# {spec.name}\n\n'
            f'Description: {command_description}\n'
            f'{usage_line}'
            f'Model: {spec.model}\n'
            f'Allowed tools: {", ".join(spec.tools)}\n\n'
            f'{spec.body}'
        )

    def _agent_runtime_name(self, agent_name: str) -> str:
        placeholder_name = self._extract_placeholder_name(agent_name)
        if placeholder_name is not None:
            return f'respec-{{{placeholder_name}}}-agent'
        if agent_name.startswith('respec-'):
            return f'respec-{agent_name[len("respec-") :]}-agent'
        return f'respec-{agent_name}-agent'

    def _render_agent_toml(self, spec: AgentSpec, agent_runtime_name: str) -> str:
        instructions = spec.body.rstrip().replace('"""', '\\"""')
        return (
            f'name = "{self._toml_quote(agent_runtime_name)}"\n'
            f'description = "{self._toml_quote(spec.description)}"\n'
            f'model = "{self._toml_quote(spec.model)}"\n'
            'sandbox_mode = "workspace-write"\n'
            'developer_instructions = """\n'
            f'{instructions}\n'
            '"""\n'
        )

    def _extract_placeholder_name(self, agent_name: str) -> str | None:
        if agent_name.startswith('{{') and agent_name.endswith('}}'):
            inner = agent_name[2:-2].strip()
            return inner if inner else None
        if agent_name.startswith('{') and agent_name.endswith('}'):
            inner = agent_name[1:-1].strip()
            return inner if inner else None
        return None

    def _allow_implicit_command_invocation(self, command_name: str) -> bool:
        if command_name in _INTERNAL_COMMAND_SKILLS:
            return False
        if command_name in _PREFLIGHT_COMMAND_SKILLS:
            return True
        if command_name in _PRIMARY_COMMAND_SKILLS:
            return True
        if command_name in _SECONDARY_COMMAND_PARENTS:
            return True
        return True

    def _command_short_description(self, command_name: str, base_description: str) -> str:
        usage_note = self._command_usage_note(command_name)
        if usage_note is None:
            return base_description
        if base_description:
            return f'{base_description} {usage_note}'
        return usage_note

    def _command_default_prompt(self, command_name: str, argument_hint: str) -> str:
        base_prompt = (
            f'Run the {command_name} workflow with arguments: {argument_hint}.'
            if argument_hint
            else f'Run the {command_name} workflow.'
        )
        usage_note = self._command_usage_note(command_name)
        if usage_note is None:
            return base_prompt
        return f'{usage_note} {base_prompt}'

    def _command_usage_note(self, command_name: str) -> str | None:
        if command_name in _INTERNAL_COMMAND_SKILLS:
            return 'Internal workflow used by `respec-plan`; do not invoke directly.'
        if command_name in _PREFLIGHT_COMMAND_SKILLS:
            return 'Preflight workflow; run before `respec-plan`, `respec-phase`, `respec-code`, and `respec-patch`.'
        if command_name in _SECONDARY_COMMAND_PARENTS:
            parent_command = _SECONDARY_COMMAND_PARENTS[command_name]
            return f'Typically orchestrated by `{parent_command}`; direct use is for edge cases.'
        return None

    def _command_usage_hint(self, command_name: str, argument_hint: str) -> str | None:
        if command_name in _INTERNAL_COMMAND_SKILLS:
            return None
        if argument_hint:
            return f'${command_name} {argument_hint}'
        return f'${command_name}'

    def _command_display_name(self, command_name: str) -> str:
        return self._title_name(command_name)

    def _agent_display_name(self, agent_runtime_name: str) -> str:
        return self._title_name(agent_runtime_name)

    def _title_name(self, raw_name: str) -> str:
        return raw_name.replace('-', ' ').title()

    def _render_openai_yaml(
        self,
        display_name: str,
        short_description: str,
        default_prompt: str,
        allow_implicit_invocation: bool,
    ) -> str:
        implicit = 'true' if allow_implicit_invocation else 'false'
        return (
            'interface:\n'
            f'  display_name: "{self._yaml_quote(display_name)}"\n'
            f'  short_description: "{self._yaml_quote(short_description)}"\n'
            f'  default_prompt: "{self._yaml_quote(default_prompt)}"\n'
            'policy:\n'
            f'  allow_implicit_invocation: {implicit}\n'
        )

    def _yaml_quote(self, value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def _toml_quote(self, value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')
