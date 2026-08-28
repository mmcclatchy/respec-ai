import json
import subprocess
import sys
from pathlib import Path

from src.cli.commands import frontend_preflight
from src.platform.standards_config import _toml_quote


def _write_stack_toml(project_path: Path, *, dev_command: str = '', base_url: str = '', seed_command: str = '') -> None:
    config_dir = project_path / '.respec-ai' / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'stack.toml').write_text(
        f"""schema_version = 2

[project]
primary_language = "typescript"
languages = ["typescript"]

[execution]
standards_profile = "opt_in"
recommend_preflight = true

[language.typescript]
runtime_version = ""
package_manager = ""
backend_framework = ""
frontend_framework = "react"
database = ""
api_style = ""
architecture = ""
async_runtime = false
css_framework = ""
ui_components = ""
type_checker = ""
test_runner = ""
test_command = ""
coverage_command = ""
type_check_command = ""
lint_command = ""
dev_command = {_toml_quote(dev_command)}
base_url = {_toml_quote(base_url)}
seed_command = {_toml_quote(seed_command)}
storage_state_path = ""
""",
        encoding='utf-8',
    )


def _run(action: str, tmp_path: Path, **kwargs: object) -> dict:
    # Each invocation is a real, separate process -- exactly how respec-ai/phase 7 will call
    # this command, and the only way an orphan-detection test is meaningful: a dev server
    # spawned and then abandoned by a still-alive parent (in-process test harness) would sit as
    # an unreaped zombie regardless of whether the kill worked, since only its parent can reap
    # it. A real invocation exits, the child is re-parented to init, and init reaps it -- so
    # only a genuine subprocess boundary here can tell a real leak apart from that artifact.
    args = [
        sys.executable,
        '-c',
        'import sys; from src.cli.main import main; sys.exit(main())',
        'frontend-preflight',
        f'--{action}',
    ]
    timeout = kwargs.pop('timeout', None)
    if timeout is not None:
        args += ['--timeout', str(timeout)]
    coding_loop_id = kwargs.pop('coding_loop_id', None)
    if coding_loop_id is not None:
        args += ['--coding-loop-id', str(coding_loop_id)]
    review_iteration = kwargs.pop('review_iteration', None)
    if review_iteration is not None:
        args += ['--review-iteration', str(review_iteration)]

    result = subprocess.run(
        args, cwd=tmp_path, capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestFrontendPreflightFailurePaths:
    def test_missing_dev_command_reports_not_ready_and_exits_zero(
        self, tmp_path: Path
    ) -> None:
        """B5: no config -> ready: false with a reason, exit 0 (not an error)."""

        output = _run('start', tmp_path)

        assert output['ready'] is False
        assert 'dev_command' in output['reason']
        assert not (tmp_path / '.respec-ai' / 'run' / frontend_preflight.PIDFILE_NAME).exists()

    def test_dev_command_that_exits_immediately_reports_not_ready_with_log_tail(
        self, tmp_path: Path
    ) -> None:
        """B6: a dev_command exiting non-zero -> ready: false, log_tail present, exit 0, no orphan."""
        dev_command = f'{sys.executable} -c "import sys; print(\'boom\'); sys.exit(1)"'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url='http://127.0.0.1:1/')

        output = _run('start', tmp_path, timeout=5)

        assert output['ready'] is False
        assert 'exited' in output['reason']
        assert 'boom' in output['log_tail']
        assert not (tmp_path / '.respec-ai' / 'run' / frontend_preflight.PIDFILE_NAME).exists()


class TestFrontendPreflightHappyPath:
    def test_start_returns_ready_with_reachable_base_url_within_timeout(
        self, tmp_path: Path
    ) -> None:
        """B1."""
        port = _free_port()
        dev_command = f'{sys.executable} -m http.server {port} --bind 127.0.0.1 --directory {tmp_path}'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url=f'http://127.0.0.1:{port}/')

        try:
            output = _run('start', tmp_path, timeout=10)

            assert output['ready'] is True
            assert output['base_url'] == f'http://127.0.0.1:{port}/'
            assert output['pid']
            assert Path(output['scratch_dir']).is_dir()
            assert Path(output['log_path']).exists()
        finally:
            _run('stop', tmp_path)

    def test_start_called_twice_reuses_the_running_server(self, tmp_path: Path) -> None:
        """B2, the stronger half: --start itself must not spawn a second process either."""
        port = _free_port()
        dev_command = f'{sys.executable} -m http.server {port} --bind 127.0.0.1 --directory {tmp_path}'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url=f'http://127.0.0.1:{port}/')

        try:
            first = _run('start', tmp_path, timeout=10)
            second = _run('start', tmp_path, timeout=10)

            assert first['pid'] == second['pid']
            assert second['ready'] is True
        finally:
            _run('stop', tmp_path)

    def test_status_called_twice_does_not_start_a_second_server(
        self, tmp_path: Path
    ) -> None:
        """B2."""
        port = _free_port()
        dev_command = f'{sys.executable} -m http.server {port} --bind 127.0.0.1 --directory {tmp_path}'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url=f'http://127.0.0.1:{port}/')

        try:
            started = _run('start', tmp_path, timeout=10)
            status_one = _run('status', tmp_path)
            status_two = _run('status', tmp_path)

            assert status_one['pid'] == started['pid'] == status_two['pid']
            assert status_one['ready'] is True
            assert status_two['ready'] is True
        finally:
            _run('stop', tmp_path)

    def test_stop_leaves_no_process_and_no_orphaned_children(
        self, tmp_path: Path
    ) -> None:
        """B3: the dev_command forks a child; --stop must kill the whole group."""
        port = _free_port()
        marker = tmp_path / 'child.pid'
        child_script = tmp_path / 'child.py'
        child_script.write_text(
            "import os, sys, time\n"
            f"open({str(marker)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(60)\n",
            encoding='utf-8',
        )
        launcher = tmp_path / 'launch.sh'
        launcher.write_text(
            f'#!/bin/sh\n'
            f'{sys.executable} {child_script} &\n'
            f'exec {sys.executable} -m http.server {port} --bind 127.0.0.1 --directory {tmp_path}\n',
            encoding='utf-8',
        )
        launcher.chmod(0o755)
        dev_command = f'/bin/sh {launcher}'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url=f'http://127.0.0.1:{port}/')

        started = _run('start', tmp_path, timeout=10)
        assert started['ready'] is True

        import time as _time

        deadline = _time.monotonic() + 5
        while _time.monotonic() < deadline and not marker.exists():
            _time.sleep(0.05)
        assert marker.exists()
        child_pid = int(marker.read_text().strip())

        _run('stop', tmp_path)

        assert not frontend_preflight._pid_alive(started['pid'])
        assert not frontend_preflight._pid_alive(child_pid)
        assert not (tmp_path / '.respec-ai' / 'run' / frontend_preflight.PIDFILE_NAME).exists()

    def test_a_base_url_that_never_responds_reports_not_ready_at_timeout_and_cleans_up(
        self, tmp_path: Path
    ) -> None:
        """B7: the process must be killed at timeout, no orphan left behind."""
        dev_command = f'{sys.executable} -c "import time; time.sleep(60)"'
        _write_stack_toml(tmp_path, dev_command=dev_command, base_url='http://127.0.0.1:1/')

        output = _run('start', tmp_path, timeout=1)

        assert output['ready'] is False
        assert 'reachable' in output['reason']
        assert not (tmp_path / '.respec-ai' / 'run' / frontend_preflight.PIDFILE_NAME).exists()

    def test_scratch_dir_is_created_and_returned(self, tmp_path: Path) -> None:
        """B4 (creation/return half; gitignore/commit-exclusion covered separately)."""

        output = _run('start', tmp_path, coding_loop_id='loop-7', review_iteration='3')

        expected = tmp_path / '.respec-ai' / 'run' / 'review' / 'loop-7' / '3'
        assert Path(output['scratch_dir']) == expected
        assert expected.is_dir()

    def test_stop_is_safe_to_call_when_nothing_is_running(
        self, tmp_path: Path
    ) -> None:

        output = _run('stop', tmp_path)

        assert output['stopped'] is True

    def test_status_reports_playwright_mcp_registration_state(
        self, tmp_path: Path
    ) -> None:
        """B8."""

        output = _run('status', tmp_path)

        assert 'playwright_mcp_registered' in output
        assert output['playwright_mcp_registered'] is False

    def test_seed_runs_configured_seed_command(self, tmp_path: Path) -> None:
        marker = tmp_path / 'seeded.txt'
        _write_stack_toml(
            tmp_path,
            seed_command=f'{sys.executable} -c "open(\'{marker.name}\', \'w\').write(\'ok\')"',
        )

        output = _run('seed', tmp_path)

        assert output['seeded'] is True
        assert marker.exists()

    def test_seed_without_configured_seed_command_reports_and_does_not_fail(
        self, tmp_path: Path
    ) -> None:

        output = _run('seed', tmp_path)

        assert output['seeded'] is False
        assert 'seed_command' in output['reason']
