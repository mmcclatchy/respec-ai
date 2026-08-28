import json
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from src.cli.config.claude_config import ClaudeConfigError
from src.cli.config.codex_config import CodexConfigError
from src.cli.config.gitignore import ensure_gitignore_entries
from src.cli.config.global_config import load_global_models
from src.cli.config.package_info import PackageInfoError, get_package_version
from src.cli.config.project_models import (
    get_project_model_overrides,
    load_project_config_if_exists,
    provider_for_tui,
    save_project_config,
    set_project_model_overrides,
)
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.services.best_practices_preflight import ensure_best_practices_ready
from src.cli.services.tui_model_setup import run_tui_model_setup
from src.cli.ui.console import console, print_error, print_info, print_warning
from src.cli.ui.formatters import print_setup_complete
from src.mcp.tools import register_all_tools
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_selector import TuiType


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '-p',
        '--platform',
        choices=['linear', 'github', 'markdown'],
        help='Platform type for workflow integration (defaults to existing project config)',
    )
    parser.add_argument(
        '--tui',
        choices=[t.value for t in TuiType],
        help='Terminal UI to generate files for (defaults to existing project config)',
    )
    parser.add_argument(
        '--skip-mcp-registration',
        action='store_true',
        help='Skip automatic MCP server registration',
    )
    parser.add_argument(
        '--skip-best-practices-setup',
        action='store_true',
        help='Skip best-practices-rag check/setup preflight',
    )
    parser.add_argument(
        '--pin-models',
        action='store_true',
        help='Pin current global model mapping for selected TUI into project config',
    )
    parser.add_argument(
        '-y',
        '--yes',
        action='store_true',
        help='Skip setup confirmation prompts where possible',
    )
    parser.add_argument(
        '--aa-key',
        help='Artificial Analysis API key for model benchmark recommendations',
    )
    parser.add_argument(
        '--exa-key',
        help='Exa API key for OpenCode rate limit lookup',
    )


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        config = load_project_config_if_exists(project_path)
        config_dir = project_path / '.respec-ai' / 'config'
        if config is None:
            print_error('respec-ai is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1
        if not config_dir.exists():
            print_error('Initialized project is missing required .respec-ai/config/ directory.')
            print_warning('Run: respec-ai init --force --platform [linear|github|markdown]')
            return 1

        platform = args.platform or config.get('platform')
        if not platform:
            print_error('Platform not set in config and not provided.')
            print_warning('Run: respec-ai sync --platform [linear|github|markdown]')
            return 1

        tui = args.tui or config.get('tui') or TuiType.CLAUDE_CODE.value
        try:
            tui_type = TuiType(tui)
        except ValueError:
            print_error(f'Unsupported TUI in config or args: {tui}')
            print_warning('Use --tui [claude-code|opencode|codex]')
            return 1

        result = run_tui_model_setup(tui_type, args, auto_apply=False)
        if result != 0:
            return result

        provider = provider_for_tui(tui_type)
        if args.pin_models and provider:
            global_models = load_global_models(provider)
            if global_models:
                set_project_model_overrides(config, provider, global_models)
            else:
                print_warning(f'No global {provider} model mapping found to pin.')

        model_overrides = get_project_model_overrides(config, provider) if provider else {}

        platform_type = PlatformType(platform)
        tui_adapter = get_tui_adapter(tui_type, model_overrides=model_overrides)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Regenerating templates...', total=None)

            mcp = FastMCP('template-generator')
            register_all_tools(mcp)

            files_written, _commands_count, _agents_count = generate_templates(
                orchestrator, project_path, platform_type, mcp=mcp, tui_adapter=tui_adapter
            )

            progress.update(task, description='Updating project configuration...')
            config['project_name'] = config.get('project_name') or project_path.name
            config['platform'] = platform
            config['tui'] = tui
            config['version'] = get_package_version()
            if 'created_at' not in config:
                config['created_at'] = datetime.now().isoformat()
            save_project_config(project_path, config)
            ensure_gitignore_entries(project_path)

            mcp_registered = _setup_mcp_server(args, progress, task, tui_adapter, project_path)
            progress.update(task, description='Complete!', completed=True)

        if not ensure_best_practices_ready(
            tui=tui,
            yes=bool(args.yes),
            skip_setup=bool(args.skip_best_practices_setup),
        ):
            print_warning('Project sync completed, but best-practices-rag preflight failed.')
            return 1

        print_setup_complete(
            project_path=project_path,
            platform=platform,
            files_created=len(files_written),
            mcp_registered=mcp_registered,
            tui_display_name=tui_adapter.display_name,
            command_examples=[
                tui_adapter.render_command_invocation(
                    'respec-plan', '[plan-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-roadmap', '[plan-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-phase', '[plan-name] [phase-name]', '', requires_user_interaction=False
                ),
                tui_adapter.render_command_invocation(
                    'respec-code', '[plan-name] [phase-name]', '', requires_user_interaction=False
                ),
            ],
        )
        return 0

    except json.JSONDecodeError as e:
        print_error(f'Config file is corrupted: {e}')
        print_warning('Delete .respec-ai/config.json and run: respec-ai init')
        return 1
    except ValueError as e:
        print_error(f'Invalid platform: {e}')
        return 1
    except Exception as e:
        print_error(f'Sync failed: {e}')
        return 1


def _setup_mcp_server(
    args: Namespace,
    progress: Progress,
    task: TaskID,
    tui_adapter: TuiAdapter,
    project_path: Path,
) -> bool:
    if args.skip_mcp_registration:
        return False

    progress.update(task, description='Verifying Docker installation...')
    try:
        docker_manager = DockerManager()
    except DockerManagerError as e:
        print_warning(f'Docker check failed: {e}')
        print_warning('MCP server requires Docker. Install Docker and try again.')
        print_warning('Run respec-ai register-mcp to register manually later')
        return False

    try:
        progress.update(task, description='Checking Docker image...')
        if not docker_manager.verify_image_exists():
            progress.update(task, description='Pulling Docker image...')
            try:
                docker_manager.pull_image()
            except DockerManagerError:
                print_warning('Failed to pull image from registry')
                print_info('Run: respec-ai docker build')
                print_info('Then: respec-ai register-mcp')

        if not docker_manager.verify_image_exists():
            return False

        progress.update(task, description='Starting MCP container...')
        docker_manager.ensure_running()

        progress.update(task, description='Registering MCP server...')
        try:
            mcp_registered = tui_adapter.register_mcp_server(project_path)
            tui_adapter.add_mcp_permissions(project_path)
            return mcp_registered
        except (ClaudeConfigError, CodexConfigError, PackageInfoError) as e:
            print_warning(f'MCP registration failed: {e}')
            print_warning('Run respec-ai register-mcp to register manually')
            return False

    except DockerManagerError as e:
        print_warning(f'Docker setup failed: {e}')
        print_warning('Run respec-ai docker pull or respec-ai docker build')
        print_warning('Then: respec-ai register-mcp')
        return False


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync project templates and tooling for current environment')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
