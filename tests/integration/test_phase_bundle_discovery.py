"""Behavioral tests for phase discovery on the bundle-directory layout (Phase 1).

These exercise the actual glob pattern the Markdown adapter emits against a real
directory tree, rather than asserting on literal path strings, so a future layout
change is caught by content/resolution divergence rather than string mismatch.
"""

from pathlib import Path

import pytest

from src.platform.adapters.markdown import MarkdownAdapter


class TestPhaseBundleDiscovery:
    @pytest.fixture
    def project_with_prefix_sharing_phases(self, tmp_path: Path) -> Path:
        phases_dir = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases'
        for name in ('auth', 'auth-tokens', 'auth-tokens-v2'):
            bundle = phases_dir / name
            bundle.mkdir(parents=True)
            (bundle / 'phase.md').write_text(f'# {name}', encoding='utf-8')
        return tmp_path

    def _discovery_glob(self, partial: str) -> str:
        adapter = MarkdownAdapter()
        return adapter.phase_discovery_pattern.replace('{PLAN_NAME}', 'my-project').replace(
            '{PHASE_NAME_PARTIAL}', partial
        )

    def test_a_phase_is_found_by_its_full_name_regardless_of_shared_prefixes(
        self, project_with_prefix_sharing_phases: Path
    ) -> None:
        project = project_with_prefix_sharing_phases

        matches = list(project.glob(self._discovery_glob('auth-tokens-v2')))

        assert len(matches) == 1
        assert matches[0].parent.name == 'auth-tokens-v2'

    def test_a_shared_prefix_surfaces_every_phase_that_shares_it(
        self, project_with_prefix_sharing_phases: Path
    ) -> None:
        project = project_with_prefix_sharing_phases

        matches = list(project.glob(self._discovery_glob('auth')))
        canonical_names = {match.parent.name for match in matches}

        assert canonical_names == {'auth', 'auth-tokens', 'auth-tokens-v2'}

    def test_canonical_phase_name_is_the_bundle_directory_not_the_file_stem(
        self, project_with_prefix_sharing_phases: Path
    ) -> None:
        project = project_with_prefix_sharing_phases

        (match,) = project.glob(self._discovery_glob('auth-tokens-v2'))

        assert match.name == 'phase.md'
        assert match.parent.name == 'auth-tokens-v2'
