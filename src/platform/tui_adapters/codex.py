import shutil
from pathlib import Path

from src.cli.config.codex_config import (
    is_mcp_server_registered,
    load_codex_config,
    register_mcp_server as _register_mcp_server,
    unregister_all_respec_servers as _unregister_all_respec_servers,
    unregister_mcp_server as _unregister_mcp_server,
)
from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter


class CodexAdapter(TuiAdapter):
    @property
    def display_name(self) -> str:
        return 'OpenAI Codex'

    @property
    def conversation_workflow_name(self) -> str:
        return 'the conversation workflow'

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
        commands_dir = self.commands_dir(project_path)
        agents_dir = self.prompts_dir(project_path)
        skills_dir = self.skills_dir(project_path)

        commands_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        for stale in commands_dir.glob('respec-*.md'):
            stale.unlink()
        for stale in agents_dir.glob('respec-*.md'):
            stale.unlink()
        for stale in skills_dir.glob('respec-*'):
            if stale.is_dir():
                shutil.rmtree(stale)

        files_written: list[Path] = []

        for cmd_spec in commands:
            command_doc = commands_dir / f'{cmd_spec.name}.md'
            command_doc.write_text(self.render_command(cmd_spec), encoding='utf-8')
            files_written.append(command_doc)

            skill_dir = skills_dir / cmd_spec.name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / 'SKILL.md'
            skill_path.write_text(self._render_command_skill(cmd_spec), encoding='utf-8')
            files_written.append(skill_path)

        for agent_spec in agents:
            agent_doc = agents_dir / f'{agent_spec.name}.md'
            agent_doc.write_text(self.render_agent(agent_spec), encoding='utf-8')
            files_written.append(agent_doc)

            skill_name = self._agent_skill_name(agent_spec.name)
            skill_dir = skills_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / 'SKILL.md'
            skill_path.write_text(self._render_agent_skill(agent_spec), encoding='utf-8')
            files_written.append(skill_path)

        return files_written

    @property
    def reasoning_model(self) -> str:
        config = load_codex_config()
        model = config.get('model')
        if isinstance(model, str) and model.strip():
            return model
        return 'gpt-5'

    @property
    def task_model(self) -> str:
        return self.reasoning_model

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
        skill_name = self._agent_skill_name(agent_name)
        lines = [f'Invoke the `{skill_name}` skill to {description}.']
        if params:
            lines.append('Input:')
            for name, value in params:
                lines.append(f'  - {name}: {value}')
        lines.append('Wait for completion before continuing.')
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

    def _render_command_skill(self, spec: CommandSpec) -> str:
        return (
            f'# {spec.name}\n\n'
            f'Description: {spec.description}\n'
            f'Model: {spec.model}\n'
            f'Allowed tools: {", ".join(spec.tools)}\n\n'
            f'{spec.body}'
        )

    def _render_agent_skill(self, spec: AgentSpec) -> str:
        skill_name = self._agent_skill_name(spec.name)
        return (
            f'# {skill_name}\n\n'
            f'Description: {spec.description}\n'
            f'Model: {spec.model}\n'
            f'Allowed tools: {", ".join(spec.tools)}\n\n'
            f'{spec.body}'
        )

    def _agent_skill_name(self, agent_name: str) -> str:
        if agent_name.startswith('{') and agent_name.endswith('}'):
            return agent_name
        if agent_name.startswith('respec-'):
            return f'respec-agent-{agent_name[len("respec-") :]}'
        return f'respec-agent-{agent_name}'
