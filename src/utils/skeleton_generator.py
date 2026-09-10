import re
from dataclasses import dataclass
from pathlib import Path

from src.utils.language_extensions import language_for_path
from src.utils.materializers import LanguageMaterializer, UnsupportedLanguageError, get_materializer
from src.utils.skeleton_types import (
    SkeletonIndexEntry,
    SkeletonMember,
    TestListEntry,
    parse_bare_signature,
    strip_tags,
)


_BULLET_PATH = re.compile(r'^-\s*`(?P<inner>[^`]+)`(?P<rest>.*)$')


@dataclass(frozen=True)
class ReconciliationChoice:
    path: str
    existing_signatures: tuple[str, ...]
    designed_signatures: tuple[str, ...]


@dataclass(frozen=True)
class UnmaterializedPath:
    path: str
    reason: str


@dataclass(frozen=True)
class SkeletonGenerationResult:
    written_paths: tuple[Path, ...]
    reconciliation_needed: tuple[ReconciliationChoice, ...]
    unmaterialized_paths: tuple[UnmaterializedPath, ...]
    unintrospectable_paths: tuple[str, ...]


@dataclass(frozen=True)
class TestGenerationResult:
    written_paths: tuple[Path, ...]
    skipped_existing: tuple[Path, ...]
    unmaterialized_paths: tuple[UnmaterializedPath, ...]


@dataclass(frozen=True)
class MergeResult:
    merged_paths: tuple[Path, ...]
    unresolved_signature_conflicts: tuple[str, ...]
    unintrospectable_paths: tuple[str, ...]


class SkeletonPathEscapesProjectError(ValueError):
    pass


def _parse_member(materializer: LanguageMaterializer | None, signature: str) -> SkeletonMember:
    remainder, tags = strip_tags(signature)
    if materializer is None:
        # Not yet known whether this path will materialize (generate_skeletons decides
        # that later) -- structural parse must still succeed so an unsupported-language
        # entry is reported as unmaterialized downstream, never a crash here (F6).
        member = parse_bare_signature(remainder)
    else:
        member = materializer.parse_signature(remainder)
    return SkeletonMember(
        class_name=member.class_name,
        member_name=member.member_name,
        params=member.params,
        return_type=member.return_type,
        tags=tags,
        required_imports=member.required_imports,
    )


def parse_skeleton_index(text: str) -> tuple[SkeletonIndexEntry, ...]:
    members_by_path: dict[str, list[SkeletonMember]] = {}
    materializer_by_path: dict[str, LanguageMaterializer | None] = {}
    for line in text.splitlines():
        bullet = _BULLET_PATH.match(line.strip())
        if not bullet:
            continue
        rest = bullet.group('rest')
        separator = ' :: '
        if separator not in rest:
            continue
        path = bullet.group('inner')
        signature = rest.split(separator, 1)[1].strip()
        if path not in materializer_by_path:
            try:
                materializer_by_path[path] = get_materializer(language_for_path(path), path)
            except UnsupportedLanguageError:
                materializer_by_path[path] = None
        members_by_path.setdefault(path, []).append(_parse_member(materializer_by_path[path], signature))
    return tuple(SkeletonIndexEntry(path=path, members=tuple(members)) for path, members in members_by_path.items())


def parse_test_list(text: str) -> tuple[TestListEntry, ...]:
    tests_by_path: dict[str, list[str]] = {}
    for line in text.splitlines():
        bullet = _BULLET_PATH.match(line.strip())
        if not bullet:
            continue
        inner = bullet.group('inner')
        if '::' not in inner:
            continue
        path, test_name = inner.split('::', 1)
        tests_by_path.setdefault(path.strip(), []).append(test_name.strip())
    return tuple(TestListEntry(path=path, test_names=tuple(names)) for path, names in tests_by_path.items())


def _resolve_within_project(project_root: Path, relative_path: str) -> Path:
    target = (project_root / relative_path).resolve()
    if not target.is_relative_to(project_root.resolve()):
        raise SkeletonPathEscapesProjectError(f'Path escapes project root: {relative_path}')
    return target


def _member_signature(member: SkeletonMember) -> str:
    qualified_name = f'{member.class_name}.{member.member_name}' if member.class_name else member.member_name
    return f'{qualified_name}({member.params}) -> {member.return_type}'


def _designed_signatures(entry: SkeletonIndexEntry) -> tuple[str, ...]:
    return tuple(_member_signature(member) for member in entry.members)


def _member_qualified_name(member: SkeletonMember) -> str:
    return f'{member.class_name}.{member.member_name}' if member.class_name else member.member_name


def _is_declined_internal(member: SkeletonMember) -> bool:
    # Step 7 (Skeleton Opt-In) is supposed to strip an "internal, consequential" entry
    # from the Skeleton Index entirely when the user doesn't select it, or relabel it
    # "internal, user-selected" when they do. This is a defensive backstop for if that
    # prose under-performs: never materialize a skeleton for an internal class the user
    # was never shown or declined (README.md cross-cutting risk #1).
    return 'internal' in member.tags and 'consequential' in member.tags and 'user-selected' not in member.tags


def _filter_declined_internals(entries: tuple[SkeletonIndexEntry, ...]) -> tuple[SkeletonIndexEntry, ...]:
    filtered = []
    for entry in entries:
        members = tuple(m for m in entry.members if not _is_declined_internal(m))
        if members:
            filtered.append(SkeletonIndexEntry(path=entry.path, members=members))
    return tuple(filtered)


def generate_skeletons(project_root: Path, entries: tuple[SkeletonIndexEntry, ...]) -> SkeletonGenerationResult:
    entries = _filter_declined_internals(entries)
    written: list[Path] = []
    reconciliation: list[ReconciliationChoice] = []
    unmaterialized: list[UnmaterializedPath] = []
    unintrospectable: list[str] = []
    for entry in entries:
        try:
            materializer = get_materializer(language_for_path(entry.path), entry.path)
        except UnsupportedLanguageError as e:
            unmaterialized.append(UnmaterializedPath(path=entry.path, reason=str(e)))
            continue

        target = _resolve_within_project(project_root, entry.path)
        if target.exists():
            extract = getattr(materializer, 'extract_existing_signatures', None)
            if extract is None:
                unintrospectable.append(entry.path)
                continue
            try:
                existing_signatures = extract(target)
            except SyntaxError as e:
                unmaterialized.append(
                    UnmaterializedPath(path=entry.path, reason=f'existing file could not be parsed: {e}')
                )
                continue
            reconciliation.append(
                ReconciliationChoice(
                    path=entry.path,
                    existing_signatures=existing_signatures,
                    designed_signatures=_designed_signatures(entry),
                )
            )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(materializer.render_skeleton_module(entry))
        written.append(target)
    return SkeletonGenerationResult(
        written_paths=tuple(written),
        reconciliation_needed=tuple(reconciliation),
        unmaterialized_paths=tuple(unmaterialized),
        unintrospectable_paths=tuple(unintrospectable),
    )


def _class_insertion_point(lines: list[str], class_name: str) -> int | None:
    class_header = re.compile(rf'^class\s+{re.escape(class_name)}\b.*:\s*$')
    for i, line in enumerate(lines):
        if not class_header.match(line):
            continue
        j = i + 1
        while j < len(lines):
            if lines[j].strip() and not lines[j].startswith((' ', '\t')):
                break
            j += 1
        return j
    return None


def merge_new_members(
    project_root: Path, entries: tuple[SkeletonIndexEntry, ...], merge_paths: frozenset[str]
) -> MergeResult:
    """Append only genuinely-new members to files the user chose to merge into.

    Never touches a member already present at the target path -- the create-only
    guarantee extends to the merge choice, not just to whole-file overwrite. A member
    whose name already exists but whose signature differs is neither appended (that
    would produce a duplicate `def`) nor treated as already satisfied (B2: a divergent
    signature must never be silently swallowed) -- it comes back as an unresolved
    conflict for the caller to surface.
    """
    merged: list[Path] = []
    unresolved: list[str] = []
    unintrospectable: list[str] = []
    for entry in entries:
        if entry.path not in merge_paths:
            continue
        target = _resolve_within_project(project_root, entry.path)
        if not target.exists():
            continue
        # Merge (append into an existing file) requires the introspection capability
        # (decisions.md "Introspection is an optional capability") -- Python has it,
        # other languages degrade to create-only rather than risking an unguarded
        # ast.parse SyntaxError on foreign source (F6).
        try:
            materializer = get_materializer(language_for_path(entry.path), entry.path)
        except UnsupportedLanguageError:
            unintrospectable.append(entry.path)
            continue

        extract = getattr(materializer, 'extract_existing_signatures', None)
        if extract is None:
            unintrospectable.append(entry.path)
            continue
        try:
            existing_signatures = set(extract(target))
        except SyntaxError:
            # A Python traceback as a phase-failure diagnostic is a Python-invisibility
            # violation (F6), not just a robustness bug -- surface the path instead.
            unintrospectable.append(entry.path)
            continue
        existing_names = {sig.split('(', 1)[0] for sig in existing_signatures}

        new_members: list[SkeletonMember] = []
        for member in entry.members:
            designed_signature = _member_signature(member)
            if designed_signature in existing_signatures:
                continue
            if _member_qualified_name(member) in existing_names:
                unresolved.append(designed_signature)
                continue
            new_members.append(member)
        if not new_members:
            continue

        lines = target.read_text().splitlines()
        for member in new_members:
            if member.class_name is None:
                lines.extend(['', *materializer.render_member_body(member, is_method=False).splitlines()])
                continue
            insert_at = _class_insertion_point(lines, member.class_name)
            if insert_at is None:
                continue
            lines[insert_at:insert_at] = ['', *materializer.render_member_body(member, is_method=True).splitlines()]
        target.write_text('\n'.join(lines) + '\n')
        merged.append(target)
    return MergeResult(
        merged_paths=tuple(merged),
        unresolved_signature_conflicts=tuple(unresolved),
        unintrospectable_paths=tuple(unintrospectable),
    )


def generate_tests(project_root: Path, entries: tuple[TestListEntry, ...]) -> TestGenerationResult:
    written: list[Path] = []
    skipped: list[Path] = []
    unmaterialized: list[UnmaterializedPath] = []
    for entry in entries:
        try:
            materializer = get_materializer(language_for_path(entry.path), entry.path)
        except UnsupportedLanguageError as e:
            unmaterialized.append(UnmaterializedPath(path=entry.path, reason=str(e)))
            continue

        target = _resolve_within_project(project_root, entry.path)
        if target.exists():
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(materializer.render_test_module(entry))
        written.append(target)
    return TestGenerationResult(
        written_paths=tuple(written), skipped_existing=tuple(skipped), unmaterialized_paths=tuple(unmaterialized)
    )
