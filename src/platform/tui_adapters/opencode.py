import json
from pathlib import Path
from typing import Any

from src.platform.tui_adapters.base import AgentSpec, CommandSpec, TuiAdapter


_MODEL_MAP = {
    'opus': 'anthropic/claude-opus-4-6',
    'sonnet': 'anthropic/claude-sonnet-4-6',
    'haiku': 'anthropic/claude-haiku-4-5',
}

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
        prompts_dir.mkdir(parents=True, exist_ok=True)

        for stale in prompts_dir.glob('respec-*.txt'):
            stale.unlink()

        files_written: list[Path] = []

        for agent_spec in agents:
            file_path = prompts_dir / f'{agent_spec.name}.txt'
            file_path.write_text(self.render_agent(agent_spec), encoding='utf-8')
            files_written.append(file_path)

        for cmd_spec in commands:
            file_path = prompts_dir / f'{cmd_spec.name}.txt'
            file_path.write_text(self.render_command(cmd_spec), encoding='utf-8')
            files_written.append(file_path)

        opencode_json_path = project_path / 'opencode.json'
        config = self._build_opencode_config(project_path, agents, commands)
        opencode_json_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        files_written.append(opencode_json_path)

        return files_written

    def model_name(self, short_name: str) -> str:
        return _MODEL_MAP.get(short_name, f'anthropic/claude-{short_name}')

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

    def add_mcp_permissions(self) -> bool:
        return True

    def is_mcp_registered(self, project_path: Path) -> bool:
        opencode_json_path = project_path / 'opencode.json'
        if not opencode_json_path.exists():
            return False
        config = json.loads(opencode_json_path.read_text(encoding='utf-8'))
        return 'respec-ai' in config.get('mcp', {})

    def config_dir_name(self) -> str:
        return '.opencode'

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
                'model': self.model_name(spec.model),
                'prompt': f'{{file:.opencode/prompts/{spec.name}.txt}}',
                **self._build_tools_block(spec.tools),
            }

        for cmd_spec in commands:
            task_agents = [t[5:-1] for t in cmd_spec.tools if t.startswith('Task(') and t.endswith(')')]
            agent_entry: dict[str, Any] = {
                'description': cmd_spec.description,
                'mode': 'primary',
                'model': self.model_name(cmd_spec.model),
                'prompt': f'{{file:.opencode/prompts/{cmd_spec.name}.txt}}',
                **self._build_tools_block(cmd_spec.tools),
            }
            if task_agents:
                agent_entry['permission'] = {'task': {'*': 'deny', **{a: 'allow' for a in task_agents}}}
            agent_block[cmd_spec.name] = agent_entry

        command_block: dict[str, Any] = {
            cmd_spec.name: {
                'description': cmd_spec.description,
                'agent': cmd_spec.name,
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
