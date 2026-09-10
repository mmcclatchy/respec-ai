from pathlib import Path

from src.cli.ui.console import print_error, print_warning


LEGACY_PHASE_MIGRATION_COMMAND = 'respec-ai migrate'
_MAX_LISTED = 5


def legacy_phase_files_in_plan(plan_dir: Path) -> list[Path]:
    """Return flat phase files directly inside one plan's phases/ directory, sorted.

    Legacy: .respec-ai/plans/<plan>/phases/<name>.md
    Bundle: .respec-ai/plans/<plan>/phases/<name>/phase.md

    The predicate is deliberately broad — any flat .md counts — because
    `respec-ai migrate` acts on exactly this set. A stricter rule would let a project be
    blocked by the generation gate while migrate reports nothing to do.
    """
    phases_dir = plan_dir / 'phases'
    if not phases_dir.exists():
        return []

    return sorted(phases_dir.glob('*.md'))


def find_legacy_phase_files(project_path: Path) -> list[Path]:
    plans_root = project_path / '.respec-ai' / 'plans'
    if not plans_root.exists():
        return []

    return sorted(
        phase_file
        for plan_dir in plans_root.iterdir()
        if plan_dir.is_dir()
        for phase_file in legacy_phase_files_in_plan(plan_dir)
    )


def legacy_phase_file_summary(count: int) -> str:
    return f'{count} legacy phase file{"s" if count != 1 else ""}'


def blocks_template_generation(project_path: Path) -> bool:
    """Report and block when a project still uses the flat phase layout.

    Agent templates address phases only at the bundle path, so generating them for a
    legacy project would produce agents that cannot find its phases. Blocking every
    generation entry point is what forces the migration.
    """
    legacy_files = find_legacy_phase_files(project_path)
    if not legacy_files:
        return False

    count = len(legacy_files)
    print_error(f'Legacy phase layout detected: {legacy_phase_file_summary(count)}')
    for phase_file in legacy_files[:_MAX_LISTED]:
        print_error(f'- {phase_file.relative_to(project_path)}')
    if count > _MAX_LISTED:
        print_error(f'- ... and {count - _MAX_LISTED} more')

    print_warning(f'Run: {LEGACY_PHASE_MIGRATION_COMMAND}')
    print_warning('Resolve any conflicts it reports, then retry.')
    return True
