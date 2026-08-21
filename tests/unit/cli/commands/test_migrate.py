from argparse import Namespace
from pathlib import Path

import pytest

from src.cli.commands import migrate


def _write(path: Path, content: str = 'content') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _read_all_files(root: Path) -> dict[Path, str]:
    return {path.relative_to(root): path.read_text(encoding='utf-8') for path in root.rglob('*') if path.is_file()}


def _init_project(project_path: Path) -> None:
    _write(project_path / '.respec-ai' / 'config.json', '{"platform": "markdown"}')


@pytest.fixture
def legacy_plan(tmp_path: Path) -> Path:
    """A plan with both `phases/{name}.md` and a populated `phases/{name}/` directory.

    This is the dangerous case (finding F19): naive handling silently loses the
    pre-existing directory contents when the legacy file is moved in.
    """
    _init_project(tmp_path)
    plans_root = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases'
    _write(plans_root / 'auth.md', 'auth phase content')
    _write(plans_root / 'auth' / 'tasks' / 'task-1.md', 'existing task content')
    _write(plans_root / 'auth-tokens.md', 'auth-tokens phase content')
    _write(plans_root / 'auth-tokens-v2.md', 'auth-tokens-v2 phase content')
    return tmp_path


class TestMigrateCommand:
    def test_migration_preserves_phase_content_and_existing_directory_contents(
        self, legacy_plan: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(legacy_plan)
        before = _read_all_files(legacy_plan)

        result = migrate.run(Namespace(plan=None))

        assert result == 0
        after = _read_all_files(legacy_plan)
        assert set(before.values()) == set(after.values())
        assert (legacy_plan / '.respec-ai/plans/my-project/phases/auth/tasks/task-1.md').read_text() == (
            'existing task content'
        )

    def test_migration_moves_legacy_file_into_bundle_directory(
        self, legacy_plan: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(legacy_plan)

        migrate.run(Namespace(plan=None))

        phases = legacy_plan / '.respec-ai/plans/my-project/phases'
        assert not (phases / 'auth.md').exists()
        assert (phases / 'auth/phase.md').read_text() == 'auth phase content'
        assert (phases / 'auth-tokens/phase.md').read_text() == 'auth-tokens phase content'
        assert (phases / 'auth-tokens-v2/phase.md').read_text() == 'auth-tokens-v2 phase content'

    def test_migrating_twice_changes_nothing_the_second_time(
        self, legacy_plan: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(legacy_plan)
        migrate.run(Namespace(plan=None))
        after_first = _read_all_files(legacy_plan)

        result = migrate.run(Namespace(plan=None))

        assert result == 0
        assert _read_all_files(legacy_plan) == after_first

    def test_migration_refuses_when_bundle_directory_already_has_a_phase_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        phases = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases'
        _write(phases / 'auth.md', 'legacy content')
        _write(phases / 'auth' / 'phase.md', 'already-migrated content')

        result = migrate.run(Namespace(plan=None))

        assert result == 1
        assert (phases / 'auth.md').read_text() == 'legacy content'
        assert (phases / 'auth' / 'phase.md').read_text() == 'already-migrated content'

    def test_migration_refusal_on_one_phase_does_not_block_migrating_others(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        phases = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases'
        _write(phases / 'auth.md', 'legacy content')
        _write(phases / 'auth' / 'phase.md', 'already-migrated content')
        _write(phases / 'billing.md', 'billing content')

        result = migrate.run(Namespace(plan=None))

        assert result == 1
        assert (phases / 'billing/phase.md').read_text() == 'billing content'
        assert not (phases / 'billing.md').exists()

    def test_refuses_when_project_is_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        result = migrate.run(Namespace(plan=None))

        assert result == 1

    def test_succeeds_as_a_noop_when_initialized_project_has_no_plans_yet(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = migrate.run(Namespace(plan=None))

        assert result == 0

    def test_migrating_a_project_already_on_the_bundle_layout_makes_no_changes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        phases = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases'
        _write(phases / 'auth' / 'phase.md', 'auth content')
        before = _read_all_files(tmp_path)

        result = migrate.run(Namespace(plan=None))

        assert result == 0
        assert _read_all_files(tmp_path) == before
