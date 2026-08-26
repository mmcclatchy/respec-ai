from pathlib import Path
from typing import Protocol, runtime_checkable

from src.utils.skeleton_generator import SkeletonIndexEntry, SkeletonMember, TestListEntry


class UnsupportedLanguageError(ValueError):
    def __init__(self, path: str, language: str | None) -> None:
        self.path = path
        self.language = language
        detail = f'language {language!r}' if language else 'unrecognized file extension'
        super().__init__(f'No materializer registered for {path} ({detail})')


@runtime_checkable
class LanguageMaterializer(Protocol):
    not_implemented_sentinel: str

    def parse_signature(self, remainder: str) -> SkeletonMember: ...

    def render_skeleton_module(self, entry: SkeletonIndexEntry) -> str: ...

    def render_test_module(self, entry: TestListEntry) -> str: ...

    def test_path_convention(self) -> str: ...

    # Optional capability (README.md "the expensive capability is the optional one";
    # decisions.md "introspection is an optional capability"). Absence means the
    # language degrades to create-only -- never a silent skip, never a crash.
    def extract_existing_signatures(self, path: Path) -> tuple[str, ...]: ...

    # Optional, cheap capabilities consumed by design_conformance.py so a new
    # language's conformance support lives entirely in its own materializer module
    # (README.md cross-cutting risk #1: the boundary test). Absence degrades to "no
    # cross-module/test-file awareness for this language" -- never a crash, never a
    # false blocker.
    test_file_suffixes: tuple[str, ...]

    def find_exported_names(self, source: str) -> frozenset[str]: ...

    def references_name(self, source: str, target_name: str, member_name: str, is_method: bool) -> bool: ...
