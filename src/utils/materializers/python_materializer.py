from pathlib import Path

from src.utils import skeleton_generator
from src.utils.skeleton_generator import SkeletonIndexEntry, SkeletonMember, TestListEntry


class PythonMaterializer:
    not_implemented_sentinel = 'raise NotImplementedError'
    # Python's test-file convention (test_ prefix, tests/ directory) is already covered
    # by design_conformance.py's language-neutral _TEST_PATH_MARKERS -- no suffix-based
    # convention to add here.
    test_file_suffixes: tuple[str, ...] = ()

    def parse_signature(self, remainder: str) -> SkeletonMember:
        return skeleton_generator.parse_python_signature(remainder)

    def render_skeleton_module(self, entry: SkeletonIndexEntry) -> str:
        return skeleton_generator.render_skeleton_module(entry)

    def render_test_module(self, entry: TestListEntry) -> str:
        return skeleton_generator.render_test_module(entry)

    def test_path_convention(self) -> str:
        return 'tests/ directory, mirrors src/ structure -- test_{function}_{scenario} naming'

    def extract_existing_signatures(self, path: Path) -> tuple[str, ...]:
        return skeleton_generator.extract_existing_signatures(path)
