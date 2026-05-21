import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from fastmcp import FastMCP
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.cli.config.package_info import get_package_version
from src.cli.config.project_models import get_project_model_overrides, provider_for_tui
from src.cli.ui.console import console, print_error, print_info, print_success, print_warning
from src.mcp.tools import register_all_tools
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.standards_config import validate_project_config
from src.platform.template_generator import generate_templates
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


_DETECTION_ORDER: tuple[TuiType, ...] = (
    TuiType.CLAUDE_CODE,
    TuiType.OPENCODE,
    TuiType.CODEX,
)

_ARTIFACT_DIRS_BY_TUI: dict[TuiType, tuple[str, ...]] = {
    TuiType.CLAUDE_CODE: ('.claude/agents', '.claude/commands'),
    TuiType.OPENCODE: ('.opencode/prompts/agents', '.opencode/prompts/commands'),
    TuiType.CODEX: ('.codex/agents', '.codex/skills'),
}


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help='Regenerate templates even if version is current',
    )
    parser.add_argument(
        '--tui',
        choices=['auto', *(t.value for t in TuiType), 'all'],
        default='auto',
        help='TUI target (default: auto)',
    )


def _has_any_files(directory: Path) -> bool:
    if not directory.exists() or not directory.is_dir():
        return False
    return any(path.is_file() for path in directory.rglob('*'))


def _detect_tuis_with_artifacts(project_path: Path) -> list[TuiType]:
    detected: list[TuiType] = []
    for tui_type in _DETECTION_ORDER:
        dirs = _ARTIFACT_DIRS_BY_TUI[tui_type]
        if any(_has_any_files(project_path / rel_path) for rel_path in dirs):
            detected.append(tui_type)
    return detected


def run(args: Namespace, version_override: str | None = None) -> int:
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            print_error('respec-ai is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        config_dir = project_path / '.respec-ai' / 'config'
        if not config_dir.exists():
            print_error('Initialized project is missing required .respec-ai/config/ directory.')
            print_warning('Run: respec-ai init --force --platform [linear|github|markdown]')
            return 1
        standards_errors = validate_project_config(project_path)
        if standards_errors:
            print_error('Invalid standards config. Regeneration aborted.')
            for err in standards_errors:
                print_error(f'- {err}')
            print_warning('Fix standards config: respec-ai standards init|validate')
            return 1

        config = json.loads(config_path.read_text(encoding='utf-8'))
        current_version = config.get('version', 'unknown')
        package_version = version_override or get_package_version()
        platform = config.get('platform')

        if not platform:
            print_error('Platform not set in config')
            print_warning('Delete .respec-ai/config.json and run: respec-ai init')
            return 1

        if current_version == package_version and not args.force:
            print_info(f'Templates are already up to date (v{package_version})')
            print_info('Use --force to regenerate anyway')
            return 0

        platform_type = PlatformType(platform)
        target = getattr(args, 'tui', 'auto')
        detected_tuis = _resolve_target_tuis(project_path, config, target)
        if not detected_tuis:
            print_error('No TUI target available for regeneration in this project')
            print_warning('Run: respec-ai sync --tui [claude-code|opencode|codex]')
            return 1

        orchestrator = PlatformOrchestrator.create_with_default_config()
        successful_regenerations: list[tuple[TuiType, str, int, int]] = []
        failures: list[tuple[TuiType, str, str]] = []

        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Regenerating templates...', total=None)

            mcp = FastMCP('template-generator')
            register_all_tools(mcp)

            for tui_type in detected_tuis:
                provider = provider_for_tui(tui_type)
                model_overrides = get_project_model_overrides(config, provider) if provider else {}
                tui_adapter = get_tui_adapter(tui_type, model_overrides=model_overrides)
                progress.update(task, description=f'Regenerating {tui_adapter.display_name} templates...')
                try:
                    _, commands_count, agents_count = generate_templates(
                        orchestrator, project_path, platform_type, mcp=mcp, tui_adapter=tui_adapter
                    )
                    successful_regenerations.append((tui_type, tui_adapter.display_name, commands_count, agents_count))
                except Exception as e:
                    failures.append((tui_type, tui_adapter.display_name, str(e)))

            progress.update(task, description='Updating configuration...')

            if not failures:
                config['version'] = package_version
                config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

            progress.update(task, description='Complete!', completed=True)

        console.print()
        if failures:
            print_warning('Template regeneration completed with errors')
        else:
            if args.force:
                print_success('Templates regenerated successfully')
            else:
                print_success(f'Templates updated: v{current_version} → v{package_version}')

        for _tui, display_name, commands_count, agents_count in successful_regenerations:
            print_success(f'{display_name}: regenerated {commands_count} commands and {agents_count} agents')

        for _tui, display_name, error in failures:
            print_warning(f'{display_name}: regenerate failed: {error}')

        console.print()
        for _tui, display_name, _commands_count, _agents_count in successful_regenerations:
            print_warning(f'Restart {display_name} to activate the updated templates')
        console.print()

        if failures:
            return 1
        return 0

    except json.JSONDecodeError as e:
        print_error(f'Config file is corrupted: {e}')
        print_warning('Delete .respec-ai/config.json and run: respec-ai init')
        return 1

    except ValueError as e:
        print_error(f'Invalid platform in config: {e}')
        return 1

    except Exception as e:
        print_error(f'Regenerate failed: {e}')
        return 1


def _resolve_target_tuis(project_path: Path, config: dict, target: str) -> list[TuiType]:
    if target == 'all':
        return list(_DETECTION_ORDER)

    if target != 'auto':
        return [TuiType(target)]

    detected = _detect_tuis_with_artifacts(project_path)
    if detected:
        return detected

    configured_tui = config.get('tui')
    if isinstance(configured_tui, str):
        try:
            return [TuiType(configured_tui)]
        except ValueError:
            return []

    return []


if __name__ == '__main__':
    parser = ArgumentParser(description='Regenerate agent and command templates')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
