import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import CLAUDE_CONFIG_PATH, ClaudeConfigError, load_claude_config
from src.platform.standards_config import load_toml_file
from src.platform.tui_selector import TuiType

RUN_DIRNAME = 'run'
PIDFILE_NAME = 'dev-server.pid'
LOG_NAME = 'dev-server.log'
SEED_LOG_NAME = 'seed.log'
DEFAULT_TIMEOUT_SECONDS = 60
_POLL_INTERVAL_SECONDS = 0.2
_LOG_TAIL_LINES = 20
_KILL_GRACE_SECONDS = 5.0


def add_arguments(parser: ArgumentParser) -> None:
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        '--start', action='store_true', help='Start the configured dev server and wait until it is reachable'
    )
    action.add_argument(
        '--status', action='store_true', help='Report whether the dev server is running and reachable'
    )
    action.add_argument('--stop', action='store_true', help='Stop the dev server and its whole process group')
    action.add_argument('--seed', action='store_true', help='Run the optional seed_command')
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help='Seconds to wait for the dev server to become reachable (--start only)',
    )
    parser.add_argument(
        '--coding-loop-id',
        default='default',
        help='Coding loop id, used to namespace the review scratch directory (--start only)',
    )
    parser.add_argument(
        '--review-iteration',
        default='1',
        help='Review iteration, used to namespace the review scratch directory (--start only)',
    )


def run(args: Namespace) -> int:
    project_path = Path.cwd().resolve()
    try:
        if args.start:
            output = _start(
                project_path,
                timeout=args.timeout,
                coding_loop_id=str(args.coding_loop_id),
                review_iteration=str(args.review_iteration),
            )
        elif args.status:
            output = _status(project_path)
        elif args.stop:
            output = _stop(project_path)
        else:
            output = _seed(project_path)
    except Exception as e:
        # A traceback here is a Python-invisibility violation -- report cleanly and let the
        # caller (the reviewer roster gate, or a human running this by hand) decide what to do.
        output = {'ready': False, 'reason': f'frontend-preflight failed: {e}'}

    print(json.dumps(output))
    return 0


def _run_dir(project_path: Path) -> Path:
    return project_path / '.respec-ai' / RUN_DIRNAME


def _pidfile(project_path: Path) -> Path:
    return _run_dir(project_path) / PIDFILE_NAME


def _logfile(project_path: Path) -> Path:
    return _run_dir(project_path) / LOG_NAME


def _scratch_dir(project_path: Path, coding_loop_id: str, review_iteration: str) -> Path:
    return _run_dir(project_path) / 'review' / coding_loop_id / review_iteration


def _load_stack_data(project_path: Path) -> dict | None:
    stack_toml = project_path / '.respec-ai' / 'config' / 'stack.toml'
    if not stack_toml.exists():
        return None
    try:
        return load_toml_file(stack_toml)
    except Exception:
        return None


def _find_dev_server_config(data: dict) -> tuple[str | None, str | None]:
    languages = data.get('project', {}).get('languages', [])
    language_tables = data.get('language', {})
    for language in languages:
        table = language_tables.get(language, {})
        dev_command = str(table.get('dev_command', '')).strip()
        base_url = str(table.get('base_url', '')).strip()
        if dev_command and base_url:
            return dev_command, base_url
    return None, None


def _find_seed_command(data: dict) -> str | None:
    languages = data.get('project', {}).get('languages', [])
    language_tables = data.get('language', {})
    for language in languages:
        seed_command = str(language_tables.get(language, {}).get('seed_command', '')).strip()
        if seed_command:
            return seed_command
    return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _kill_process_group(pid: int) -> None:
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return

    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + _KILL_GRACE_SECONDS
    while time.monotonic() < deadline and _group_alive(pgid):
        time.sleep(0.05)

    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _probe_url(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _read_pidfile(project_path: Path) -> int | None:
    pidfile = _pidfile(project_path)
    if not pidfile.exists():
        return None
    try:
        return int(pidfile.read_text(encoding='utf-8').strip())
    except ValueError:
        return None


def _log_tail(log_path: Path, lines: int = _LOG_TAIL_LINES) -> str:
    if not log_path.exists():
        return ''
    content = log_path.read_text(encoding='utf-8', errors='replace').splitlines()
    return '\n'.join(content[-lines:])


def _is_playwright_mcp_registered(project_path: Path) -> bool:
    tui = TuiType.CLAUDE_CODE.value
    config_path = project_path / '.respec-ai' / 'config.json'
    if config_path.exists():
        try:
            tui = json.loads(config_path.read_text(encoding='utf-8')).get('tui', tui)
        except json.JSONDecodeError:
            pass

    # Playwright registration is only checkable for Claude Code today -- the MCP registrar is
    # hardcoded to a single server (F28) and generalizing it to OpenCode/Codex is deferred.
    # OpenCode and Codex correctly report unregistered rather than raising.
    if tui != TuiType.CLAUDE_CODE.value:
        return False

    try:
        config = load_claude_config(CLAUDE_CONFIG_PATH)
    except ClaudeConfigError:
        return False

    return any('playwright' in name.lower() for name in config.get('mcpServers', {}))


def _start(project_path: Path, *, timeout: int, coding_loop_id: str, review_iteration: str) -> dict:
    scratch_dir = _scratch_dir(project_path, coding_loop_id, review_iteration)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    playwright_mcp_registered = _is_playwright_mcp_registered(project_path)

    data = _load_stack_data(project_path)
    dev_command, base_url = _find_dev_server_config(data) if data else (None, None)
    if not dev_command or not base_url:
        return {
            'ready': False,
            'reason': 'no dev_command configured',
            'scratch_dir': str(scratch_dir),
            'playwright_mcp_registered': playwright_mcp_registered,
        }

    run_dir = _run_dir(project_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = _logfile(project_path)
    pidfile = _pidfile(project_path)

    existing_pid = _read_pidfile(project_path)
    process: subprocess.Popen | None = None
    if existing_pid is not None and _pid_alive(existing_pid):
        if _probe_url(base_url):
            return {
                'ready': True,
                'base_url': base_url,
                'pid': existing_pid,
                'log_path': str(log_path),
                'scratch_dir': str(scratch_dir),
                'playwright_mcp_registered': playwright_mcp_registered,
            }
        pid = existing_pid
    else:
        log_fh = log_path.open('w', encoding='utf-8')
        try:
            # shell=True (not shlex.split) because dev_command is user-authored and commonly
            # carries shell syntax a naive split would break: env var prefixes
            # ("PORT=3000 npm run dev"), "&&" chains, pipes. start_new_session=True still makes
            # the shell the process-group leader, so killpg reaches the shell and everything it
            # execs or forks.
            process = subprocess.Popen(
                dev_command,
                shell=True,
                cwd=project_path,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            log_fh.close()
        pid = process.pid
        pidfile.write_text(str(pid), encoding='utf-8')

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            pidfile.unlink(missing_ok=True)
            return {
                'ready': False,
                'reason': f'dev server exited with code {process.returncode} before becoming reachable',
                'log_tail': _log_tail(log_path),
                'scratch_dir': str(scratch_dir),
                'playwright_mcp_registered': playwright_mcp_registered,
            }
        if _probe_url(base_url):
            return {
                'ready': True,
                'base_url': base_url,
                'pid': pid,
                'log_path': str(log_path),
                'scratch_dir': str(scratch_dir),
                'playwright_mcp_registered': playwright_mcp_registered,
            }
        time.sleep(_POLL_INTERVAL_SECONDS)

    _kill_process_group(pid)
    pidfile.unlink(missing_ok=True)
    return {
        'ready': False,
        'reason': f'dev server did not become reachable within {timeout}s',
        'log_tail': _log_tail(log_path),
        'scratch_dir': str(scratch_dir),
        'playwright_mcp_registered': playwright_mcp_registered,
    }


def _status(project_path: Path) -> dict:
    playwright_mcp_registered = _is_playwright_mcp_registered(project_path)
    pid = _read_pidfile(project_path)
    if pid is None or not _pid_alive(pid):
        return {
            'ready': False,
            'reason': 'dev server is not running',
            'playwright_mcp_registered': playwright_mcp_registered,
        }

    data = _load_stack_data(project_path)
    _dev_command, base_url = _find_dev_server_config(data) if data else (None, None)
    reachable = base_url is not None and _probe_url(base_url)

    output = {
        'ready': reachable,
        'base_url': base_url,
        'pid': pid,
        'log_path': str(_logfile(project_path)),
        'playwright_mcp_registered': playwright_mcp_registered,
    }
    if not reachable:
        output['reason'] = 'dev server process is running but base_url is not reachable'
    return output


def _stop(project_path: Path) -> dict:
    pid = _read_pidfile(project_path)
    pidfile = _pidfile(project_path)
    if pid is None:
        return {'stopped': True, 'reason': 'no dev server was running'}

    if _pid_alive(pid):
        _kill_process_group(pid)

    pidfile.unlink(missing_ok=True)
    return {'stopped': True}


def _seed(project_path: Path) -> dict:
    data = _load_stack_data(project_path)
    seed_command = _find_seed_command(data) if data else None
    if not seed_command:
        return {'seeded': False, 'reason': 'no seed_command configured'}

    run_dir = _run_dir(project_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / SEED_LOG_NAME

    result = subprocess.run(seed_command, shell=True, cwd=project_path, capture_output=True, text=True, check=False)
    log_path.write_text((result.stdout or '') + (result.stderr or ''), encoding='utf-8')

    if result.returncode != 0:
        return {
            'seeded': False,
            'reason': f'seed_command exited with code {result.returncode}',
            'log_tail': _log_tail(log_path),
        }
    return {'seeded': True}
