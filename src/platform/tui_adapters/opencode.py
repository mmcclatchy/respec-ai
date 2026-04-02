import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from src.cli.config.global_config import load_global_models
from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter


_BUILTIN_TOOL_MAP = {
    'Read': 'read',
    'Write': 'write',
    'Edit': 'edit',
    'Bash': 'bash',
    'Glob': 'glob',
    'Grep': 'grep',
    'LS': 'ls',
    'WebSearch': 'webSearch',
    'WebFetch': 'webFetch',
    'TodoWrite': 'todoWrite',
    'NotebookEdit': 'notebookEdit',
}


class OpenCodeAdapter(TuiAdapter):
    @property
    def display_name(self) -> str:
        return 'OpenCode'

    @property
    def conversation_workflow_name(self) -> str:
        return 'the conversation workflow'

    def commands_dir(self, project_path: Path) -> Path:
        return project_path / '.opencode' / 'commands'

    def prompts_dir(self, project_path: Path) -> Path:
        return project_path / '.opencode' / 'prompts'

    def render_agent(self, spec: AgentSpec) -> str:
        return spec.body

    def render_command(self, spec: CommandSpec) -> str:
        return spec.body

    def write_all(
        self,
        project_path: Path,
        agents: list[AgentSpec],
        commands: list[CommandSpec],
    ) -> list[Path]:
        prompts_dir = self.prompts_dir(project_path)
        agents_dir = prompts_dir / 'agents'
        commands_dir = prompts_dir / 'commands'
        agents_dir.mkdir(parents=True, exist_ok=True)
        commands_dir.mkdir(parents=True, exist_ok=True)

        for stale in prompts_dir.glob('respec-*.md'):
            stale.unlink()
        for stale in agents_dir.glob('respec-*.md'):
            stale.unlink()
        for stale in commands_dir.glob('respec-*.md'):
            stale.unlink()

        files_written: list[Path] = []

        for agent_spec in agents:
            file_path = agents_dir / f'{agent_spec.name}.md'
            file_path.write_text(self.render_agent(agent_spec), encoding='utf-8')
            files_written.append(file_path)

        for cmd_spec in commands:
            file_path = commands_dir / f'{cmd_spec.name}.md'
            file_path.write_text(self.render_command(cmd_spec), encoding='utf-8')
            files_written.append(file_path)

        opencode_json_path = project_path / 'opencode.json'
        config = self._build_opencode_config(project_path, agents, commands)
        opencode_json_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        files_written.append(opencode_json_path)

        return files_written

    @property
    def reasoning_model(self) -> str:
        models = load_global_models()
        if 'reasoning' not in models:
            raise RuntimeError("OpenCode reasoning model not configured. Run 'respec-ai opencode-models' first.")
        return models['reasoning']

    @property
    def task_model(self) -> str:
        models = load_global_models()
        if 'task' not in models:
            raise RuntimeError("OpenCode task model not configured. Run 'respec-ai opencode-models' first.")
        return models['task']

    def register_mcp_server(self, project_path: Path) -> bool:
        opencode_json_path = project_path / 'opencode.json'
        raw = opencode_json_path.read_text(encoding='utf-8') if opencode_json_path.exists() else '{}'
        config: dict[str, Any] = json.loads(raw)
        config.setdefault('$schema', 'https://opencode.ai/config.json')
        mcp: dict[str, Any] = config.setdefault('mcp', {})
        mcp['respec-ai'] = {
            'type': 'local',
            'command': ['respec-ai', 'mcp-server'],
            'enabled': True,
            'environment': {},
        }
        opencode_json_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        return True

    def add_mcp_permissions(self, project_path: Path) -> bool:
        return True

    def is_mcp_registered(self, project_path: Path) -> bool:
        opencode_json_path = project_path / 'opencode.json'
        if not opencode_json_path.exists():
            return False
        config = json.loads(opencode_json_path.read_text(encoding='utf-8'))
        return 'respec-ai' in config.get('mcp', {})

    def unregister_mcp_server(self, project_path: Path) -> bool:
        opencode_json_path = project_path / 'opencode.json'
        if not opencode_json_path.exists():
            return False
        config: dict[str, Any] = json.loads(opencode_json_path.read_text(encoding='utf-8'))
        mcp = config.get('mcp', {})
        if 'respec-ai' not in mcp:
            return False
        del mcp['respec-ai']
        opencode_json_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        return True

    def post_init_setup(self, args: Namespace) -> int:
        from src.cli.commands import opencode_model

        sync_args = Namespace(
            aa_key=getattr(args, 'aa_key', None),
            exa_key=getattr(args, 'exa_key', None),
            yes=getattr(args, 'yes', False),
            debug=False,
            no_cache=False,
        )
        from src.cli.ui.console import console

        console.print('\n[bold cyan]Configuring OpenCode model tiers...[/bold cyan]\n')
        return opencode_model.run(sync_args)

    def config_dir_name(self) -> str:
        return '.opencode'

    def plans_dir(self) -> str:
        return '.opencode/plans'

    def render_agent_invocation(
        self,
        agent_name: str,
        description: str,
        params: list[tuple[str, str]],
    ) -> str:
        lines = [
            f'Use the Task tool to launch the {agent_name} agent:',
            '',
            'CALL task:',
            f'  subagent_type: "{agent_name}"',
            '  prompt: |',
            f'    {description}.',
            '',
        ]
        if params:
            lines.append('    Parameters:')
            for name, value in params:
                lines.append(f'    - {name}: {value}')
            lines.append('')
        lines.append('Wait for agent completion before proceeding.')
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
        return f'Run /{command_name} {args_template} when ready to continue.'

    def _build_opencode_config(
        self,
        project_path: Path,
        agents: list[AgentSpec],
        commands: list[CommandSpec],
    ) -> dict[str, Any]:
        agent_block: dict[str, Any] = {}

        for spec in agents:
            agent_block[spec.name] = {
                'description': spec.description,
                'mode': 'primary' if spec.is_orchestrator else 'subagent',
                'model': spec.model,
                'prompt': f'{{file:.opencode/prompts/agents/{spec.name}.md}}',
                **self._build_tools_block(spec.tools),
            }

        for cmd_spec in commands:
            cmd_key = f'cmd-{cmd_spec.name}'
            task_agents = [t[5:-1] for t in cmd_spec.tools if t.startswith('Task(') and t.endswith(')')]
            agent_entry: dict[str, Any] = {
                'description': cmd_spec.description,
                'mode': 'primary',
                'model': cmd_spec.model,
                'prompt': f'{{file:.opencode/prompts/commands/{cmd_spec.name}.md}}',
                **self._build_tools_block(cmd_spec.tools),
            }
            if task_agents:
                agent_entry['permission'] = {'task': {'*': 'deny', **{a: 'allow' for a in task_agents}}}
            agent_block[cmd_key] = agent_entry

        command_block: dict[str, Any] = {
            cmd_spec.name: {
                'description': cmd_spec.description,
                'template': f'{{file:.opencode/prompts/commands/{cmd_spec.name}.md}}',
                'agent': f'cmd-{cmd_spec.name}',
            }
            for cmd_spec in commands
        }

        return {
            '$schema': 'https://opencode.ai/config.json',
            'agent': agent_block,
            'command': command_block,
            'mcp': {},
        }

    def _build_tools_block(self, tools: list[str]) -> dict[str, Any]:
        result: dict[str, bool] = {}
        for tool in tools:
            if tool.startswith('mcp__') or tool.startswith('Task('):
                continue
            base = tool.split('(')[0]
            oc_key = _BUILTIN_TOOL_MAP.get(base)
            if oc_key:
                result[oc_key] = True
        if result:
            return {'tools': result}
        return {}
