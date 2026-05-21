import shutil
import subprocess

from src.cli.ui.console import console, print_error, print_info, print_warning


def ensure_best_practices_ready(
    *,
    tui: str,
    yes: bool,
    skip_setup: bool,
) -> bool:
    normalized_tui = _normalize_tui_name(tui)

    if skip_setup:
        print_info('best-practices-rag preflight skipped by flag.')
        return True

    if shutil.which('best-practices-rag') is None:
        print_error('best-practices-rag is not installed or not on PATH.')
        print_info('Install: uv tool install git+https://github.com/mmcclatchy/best-practices-rag.git')
        return False

    if _run(['best-practices-rag', 'check', '--tui', normalized_tui]):
        return True

    print_warning('best-practices-rag check failed for this TUI.')
    should_setup = yes
    if not should_setup:
        response = console.input('Run best-practices-rag setup now? [Y/n] ').strip().lower()
        should_setup = response in ('', 'y', 'yes')

    if not should_setup:
        print_warning('best-practices-rag setup skipped.')
        return False

    if not _run(['best-practices-rag', 'setup', '--tui', normalized_tui]):
        print_error('best-practices-rag setup failed.')
        return False

    if not _run(['best-practices-rag', 'check', '--tui', normalized_tui]):
        print_error('best-practices-rag check failed after setup.')
        return False

    return True


def _normalize_tui_name(tui: str) -> str:
    if tui == 'claude-code':
        return 'claude'
    return tui


def _run(cmd: list[str]) -> bool:
    try:
        result = subprocess.run(cmd)
    except (FileNotFoundError, OSError) as exc:
        print_error(f'Failed to execute {" ".join(cmd)}: {exc}')
        return False
    return result.returncode == 0
