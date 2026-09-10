from argparse import Namespace
from pathlib import Path

import pytest

from src.cli.commands import migrate, regenerate, validate
from src.platform.phase_layout import find_legacy_phase_files


def _write(path: Path, content: str = 'content') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _init_project(project_path: Path) -> None:
    _write(project_path / '.respec-ai' / 'config.json', '{"platform": "markdown", "version": "0.0.0"}')
    (project_path / '.respec-ai' / 'config').mkdir(parents=True, exist_ok=True)


@pytest.fixture
def legacy_project(tmp_path: Path) -> Path:
    _init_project(tmp_path)
    phases = tmp_path / '.respec-ai' / 'plans' / 'demo' / 'phases'
    _write(phases / 'phase-1-foundation.md', 'legacy phase')
    _write(phases / 'phase-2-api/phase.md', 'already migrated')
    return tmp_path


@pytest.fixture
def bundle_project(tmp_path: Path) -> Path:
    _init_project(tmp_path)
    phases = tmp_path / '.respec-ai' / 'plans' / 'demo' / 'phases'
    _write(phases / 'phase-1-foundation/phase.md', 'bundle phase')
    _write(phases / 'phase-2-api/phase.md', 'bundle phase')
    return tmp_path


class TestFindLegacyPhaseFiles:
    def test_finds_flat_phase_files(self, legacy_project: Path) -> None:
        legacy = find_legacy_phase_files(legacy_project)

        assert [path.name for path in legacy] == ['phase-1-foundation.md']

    def test_ignores_phases_already_in_bundles(self, bundle_project: Path) -> None:
        assert find_legacy_phase_files(bundle_project) == []

    def test_empty_for_a_project_with_no_plans(self, tmp_path: Path) -> None:
        _init_project(tmp_path)

        assert find_legacy_phase_files(tmp_path) == []

    def test_empty_for_an_uninitialised_directory(self, tmp_path: Path) -> None:
        assert find_legacy_phase_files(tmp_path) == []

    def test_spans_every_plan_in_the_project(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        plans = tmp_path / '.respec-ai' / 'plans'
        _write(plans / 'alpha' / 'phases' / 'phase-1.md')
        _write(plans / 'beta' / 'phases' / 'phase-1.md')

        assert len(find_legacy_phase_files(tmp_path)) == 2

    def test_agrees_with_what_migrate_actually_moves(
        self, legacy_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The gate and migrate must share one predicate. If the gate were stricter, a
        # project could be blocked while migrate reported nothing to do - a deadlock.
        monkeypatch.chdir(legacy_project)
        assert find_legacy_phase_files(legacy_project)

        assert migrate.run(Namespace(plan=None)) == 0

        assert find_legacy_phase_files(legacy_project) == []


class TestGenerationIsBlockedOnLegacyLayout:
    def test_regenerate_refuses_and_names_the_migration_command(
        self, legacy_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(legacy_project)

        result = regenerate.run(Namespace(force=True, tui='auto'))

        assert result == 1
        output = capsys.readouterr().out
        assert 'Legacy phase layout detected' in output
        assert 'respec-ai migrate' in output
        assert 'phase-1-foundation.md' in output

    def test_regenerate_proceeds_once_the_layout_is_migrated(
        self, legacy_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(legacy_project)
        migrate.run(Namespace(plan=None))

        regenerate.run(Namespace(force=True, tui='auto'))

        assert 'Legacy phase layout detected' not in capsys.readouterr().out

    def test_init_is_not_gated(self) -> None:
        # init --force runs shutil.rmtree on .respec-ai, so it destroys the legacy layout
        # rather than inheriting it, and a fresh init has no plans at all. Gating it would
        # only obstruct a deliberate start-over.
        init_source = Path('src/cli/commands/init.py').read_text(encoding='utf-8')

        assert 'blocks_template_generation' not in init_source

    def test_every_other_generation_entry_point_is_gated(self) -> None:
        gated = ['regenerate.py', 'platform.py', 'sync.py']

        for name in gated:
            source = Path(f'src/cli/commands/{name}').read_text(encoding='utf-8')
            assert 'blocks_template_generation(project_path)' in source, name


class TestValidateReportsPhaseLayout:
    def test_reports_a_failing_check_on_a_legacy_layout(
        self, legacy_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(legacy_project)

        result = validate.run(Namespace())

        assert result == 1
        output = capsys.readouterr().out
        assert 'Phase Layout' in output
        assert 'respec-ai migrate' in output

    def test_reports_a_passing_check_on_a_bundle_layout(
        self, bundle_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(bundle_project)

        validate.run(Namespace())

        assert 'Phase bundle layout' in capsys.readouterr().out

    def test_does_not_advise_running_init_for_failures_init_cannot_fix(
        self, legacy_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(legacy_project)

        validate.run(Namespace())

        assert 'Run respec-ai init to fix missing files' not in capsys.readouterr().out
