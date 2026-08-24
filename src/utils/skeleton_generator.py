import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

_BULLET_PATH = re.compile(r'^-\s*`(?P<inner>[^`]+)`(?P<rest>.*)$')
_SIGNATURE_TAGS = ('internal', 'consequential', 'user-selected')
_SIGNATURE = re.compile(
    r'^(?:(?P<class_name>[A-Za-z_]\w*)\.)?(?P<member_name>[A-Za-z_]\w*)'
    r'\((?P<params>.*)\)\s*->\s*(?P<return_type>.+)$'
)


@dataclass(frozen=True)
class SkeletonMember:
    class_name: str | None
    member_name: str
    params: str
    return_type: str
    tags: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SkeletonIndexEntry:
    path: str
    members: tuple[SkeletonMember, ...]


@dataclass(frozen=True)
class TestListEntry:
    path: str
    test_names: tuple[str, ...]


@dataclass(frozen=True)
class ReconciliationChoice:
    path: str
    existing_signatures: tuple[str, ...]
    designed_signatures: tuple[str, ...]


@dataclass(frozen=True)
class SkeletonGenerationResult:
    written_paths: tuple[Path, ...]
    reconciliation_needed: tuple[ReconciliationChoice, ...]


@dataclass(frozen=True)
class TestGenerationResult:
    written_paths: tuple[Path, ...]
    skipped_existing: tuple[Path, ...]


@dataclass(frozen=True)
class MergeResult:
    merged_paths: tuple[Path, ...]
    unresolved_signature_conflicts: tuple[str, ...]


class SkeletonPathEscapesProjectError(ValueError):
    pass


def _strip_tags(signature: str) -> tuple[str, frozenset[str]]:
    tags: list[str] = []
    remainder = signature.strip()
    while True:
        for tag in _SIGNATURE_TAGS:
            suffix = f', {tag}'
            if remainder.endswith(suffix):
                remainder = remainder[: -len(suffix)]
                tags.append(tag)
                break
        else:
            break
    return remainder, frozenset(tags)


def _parse_member(signature: str) -> SkeletonMember:
    remainder, tags = _strip_tags(signature)
    match = _SIGNATURE.match(remainder)
    if not match:
        raise ValueError(f'Unparseable Skeleton Index signature: {signature!r}')
    return SkeletonMember(
        class_name=match.group('class_name'),
        member_name=match.group('member_name'),
        params=match.group('params').strip(),
        return_type=match.group('return_type').strip(),
        tags=tags,
    )


def parse_skeleton_index(text: str) -> tuple[SkeletonIndexEntry, ...]:
    members_by_path: dict[str, list[SkeletonMember]] = {}
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
        members_by_path.setdefault(path, []).append(_parse_member(signature))
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


def _render_member_body(member: SkeletonMember, is_method: bool) -> str:
    params = member.params
    if is_method and not params.split(',')[0].strip().startswith('self'):
        params = f'self, {params}' if params else 'self'
    indent = '    ' if is_method else ''
    lines = [f'{indent}def {member.member_name}({params}) -> {member.return_type}:']
    lines.append(f'{indent}    raise NotImplementedError')
    return '\n'.join(lines)


def render_skeleton_module(entry: SkeletonIndexEntry) -> str:
    classes: dict[str, list[SkeletonMember]] = {}
    functions: list[SkeletonMember] = []
    for member in entry.members:
        if member.class_name:
            classes.setdefault(member.class_name, []).append(member)
        else:
            functions.append(member)

    blocks: list[str] = []
    for class_name, members in classes.items():
        method_bodies = '\n\n'.join(_render_member_body(m, is_method=True) for m in members)
        blocks.append(f'class {class_name}:\n{method_bodies}')
    for member in functions:
        blocks.append(_render_member_body(member, is_method=False))

    return '\n\n\n'.join(blocks) + '\n'


def render_test_module(entry: TestListEntry) -> str:
    functions = []
    for test_name in entry.test_names:
        functions.append(f'def {test_name}() -> None:\n    raise AssertionError({test_name!r})')
    return '\n\n\n'.join(functions) + '\n'


def _render_signature(
    qualified_name: str, params: list[ast.arg], returns: ast.expr | None, is_method: bool
) -> str:
    if is_method and params and params[0].arg == 'self':
        params = params[1:]
    rendered_params = [f'{a.arg}: {ast.unparse(a.annotation)}' if a.annotation else a.arg for a in params]
    return_type = ast.unparse(returns) if returns else 'None'
    return f'{qualified_name}({", ".join(rendered_params)}) -> {return_type}'


def extract_existing_signatures(path: Path) -> tuple[str, ...]:
    """Full param+return signatures, not bare names -- a same-name divergent signature
    must be visibly different to the reconciliation menu (B2), not silently equal."""
    tree = ast.parse(path.read_text())
    signatures: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signatures.append(_render_signature(node.name, node.args.args, node.returns, is_method=False))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    signatures.append(
                        _render_signature(f'{node.name}.{item.name}', item.args.args, item.returns, is_method=True)
                    )
    return tuple(signatures)


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
    for entry in entries:
        target = _resolve_within_project(project_root, entry.path)
        if target.exists():
            reconciliation.append(
                ReconciliationChoice(
                    path=entry.path,
                    existing_signatures=extract_existing_signatures(target),
                    designed_signatures=_designed_signatures(entry),
                )
            )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_skeleton_module(entry))
        written.append(target)
    return SkeletonGenerationResult(written_paths=tuple(written), reconciliation_needed=tuple(reconciliation))


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
    for entry in entries:
        if entry.path not in merge_paths:
            continue
        target = _resolve_within_project(project_root, entry.path)
        if not target.exists():
            continue
        existing_signatures = set(extract_existing_signatures(target))
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
                lines.extend(['', *_render_member_body(member, is_method=False).splitlines()])
                continue
            insert_at = _class_insertion_point(lines, member.class_name)
            if insert_at is None:
                continue
            lines[insert_at:insert_at] = ['', *_render_member_body(member, is_method=True).splitlines()]
        target.write_text('\n'.join(lines) + '\n')
        merged.append(target)
    return MergeResult(merged_paths=tuple(merged), unresolved_signature_conflicts=tuple(unresolved))


def generate_tests(project_root: Path, entries: tuple[TestListEntry, ...]) -> TestGenerationResult:
    written: list[Path] = []
    skipped: list[Path] = []
    for entry in entries:
        target = _resolve_within_project(project_root, entry.path)
        if target.exists():
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_test_module(entry))
        written.append(target)
    return TestGenerationResult(written_paths=tuple(written), skipped_existing=tuple(skipped))
