import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.ui.console import print_error, print_info, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--plan',
        default=None,
        help='Migrate only the named plan (default: every plan under .respec-ai/plans/)',
    )


def _migrate_phase_file(phase_file: Path) -> tuple[str, str]:
    phase_name = phase_file.stem
    phase_dir = phase_file.parent / phase_name
    target = phase_dir / 'phase.md'

    if target.exists():
        return 'refused', f'{phase_name}: both {phase_file.name} and {phase_name}/phase.md already exist'

    phase_dir.mkdir(parents=True, exist_ok=True)
    phase_file.rename(target)
    return 'migrated', phase_name


def _migrate_plan(plan_dir: Path) -> tuple[list[str], list[str]]:
    migrated: list[str] = []
    refused: list[str] = []

    phases_dir = plan_dir / 'phases'
    if not phases_dir.exists():
        return migrated, refused

    for phase_file in sorted(phases_dir.glob('*.md')):
        status, message = _migrate_phase_file(phase_file)
        if status == 'migrated':
            migrated.append(message)
        else:
            refused.append(message)

    return migrated, refused


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            print_error('respec-ai is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        plans_root = project_path / '.respec-ai' / 'plans'
        plan_name = getattr(args, 'plan', None)
        if plan_name:
            plan_dir = plans_root / plan_name
            if not plan_dir.exists():
                print_error(f"Plan '{plan_name}' not found under {plans_root}")
                return 1
            plan_dirs = [plan_dir]
        elif plans_root.exists():
            plan_dirs = sorted(p for p in plans_root.iterdir() if p.is_dir())
        else:
            plan_dirs = []

        any_migrated = False
        any_refused = False

        for plan_dir in plan_dirs:
            migrated, refused = _migrate_plan(plan_dir)

            for name in migrated:
                print_success(f'{plan_dir.name}: migrated {name}')
                any_migrated = True

            for message in refused:
                print_error(f'{plan_dir.name}: refused to migrate {message}')
                any_refused = True

            if not migrated and not refused:
                print_info(f'{plan_dir.name}: nothing to migrate')

        if any_refused:
            print_warning('Some phases were not migrated. Resolve the conflicts manually and re-run.')
            return 1

        if not any_migrated:
            print_info('No legacy phase layout found. Nothing to do.')

        return 0

    except Exception as e:
        print_error(f'Migration failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Migrate legacy phase layout to bundle directories')
    add_arguments(parser)
    cli_args = parser.parse_args()
    sys.exit(run(cli_args))
