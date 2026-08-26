import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.utils.language_extensions import language_for_path

_BULLET_PATH = re.compile(r'^-\s*`(?P<inner>[^`]+)`(?P<rest>.*)$')
_SIGNATURE_TAGS = ('internal', 'consequential', 'user-selected', 'async')
_SIGNATURE = re.compile(
    r'^(?:(?P<class_name>[A-Za-z_]\w*)\.)?(?P<member_name>[A-Za-z_]\w*)'
    r'\((?P<params>.*)\)\s*->\s*(?P<return_type>.+)$'
)
# A fully-qualified dotted reference to a non-builtin type, e.g. `kb.models.BestPractice`
# or `pathlib.Path` -- the Skeleton Index convention for any type that needs an import.
# Builtin generics like `list[str]` or `tuple[str, str]` have no dot and never match.
_QUALIFIED_TYPE_REF = re.compile(r'\b(?:[a-zA-Z_]\w*\.)+([A-Z]\w*)\b')


def _extract_imports_and_bare_text(text: str) -> tuple[str, frozenset[tuple[str, str]]]:
    imports: set[tuple[str, str]] = set()

    def _replace(match: re.Match[str]) -> str:
        class_name = match.group(1)
        module_path = match.group(0)[: -(len(class_name) + 1)]
        imports.add((module_path, class_name))
        return class_name

    bare_text = _QUALIFIED_TYPE_REF.sub(_replace, text)
    return bare_text, frozenset(imports)


@dataclass(frozen=True)
class SkeletonMember:
    class_name: str | None
    member_name: str
    params: str
    return_type: str
    tags: frozenset[str] = field(default_factory=frozenset)
    required_imports: frozenset[tuple[str, str]] = field(default_factory=frozenset)


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


def parse_bare_signature(remainder: str) -> SkeletonMember:
    """Language-neutral structural parse of a tag-stripped signature: class/member
    name, and bare (un-import-extracted) params/return text. Phase 1's on-disk
    Skeleton Index grammar is uniform across languages -- phase 2 makes it
    language-aware -- so every LanguageMaterializer.parse_signature can start here."""
    match = _SIGNATURE.match(remainder)
    if not match:
        raise ValueError(f'Unparseable Skeleton Index signature: {remainder!r}')
    return SkeletonMember(
        class_name=match.group('class_name'),
        member_name=match.group('member_name'),
        params=match.group('params').strip(),
        return_type=match.group('return_type').strip(),
    )


def parse_python_signature(remainder: str) -> SkeletonMember:
    bare = parse_bare_signature(remainder)
    bare_params, param_imports = _extract_imports_and_bare_text(bare.params)
    bare_return_type, return_imports = _extract_imports_and_bare_text(bare.return_type)
    return SkeletonMember(
        class_name=bare.class_name,
        member_name=bare.member_name,
        params=bare_params,
        return_type=bare_return_type,
        required_imports=param_imports | return_imports,
    )


def _parse_member(signature: str) -> SkeletonMember:
    remainder, tags = _strip_tags(signature)
    member = parse_python_signature(remainder)
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
    keyword = 'async def' if 'async' in member.tags else 'def'
    lines = [f'{indent}{keyword} {member.member_name}({params}) -> {member.return_type}:']
    lines.append(f'{indent}    raise NotImplementedError')
    return '\n'.join(lines)


def _render_import_lines(entry: SkeletonIndexEntry) -> str:
    imports: set[tuple[str, str]] = set()
    for member in entry.members:
        imports |= member.required_imports
    return '\n'.join(f'from {module} import {name}' for module, name in sorted(imports))


def render_skeleton_module(entry: SkeletonIndexEntry) -> str:
    classes: dict[str, list[SkeletonMember]] = {}
    functions: list[SkeletonMember] = []
    for member in entry.members:
        if member.class_name:
            classes.setdefault(member.class_name, []).append(member)
        else:
            functions.append(member)

    blocks: list[str] = []
    import_lines = _render_import_lines(entry)
    if import_lines:
        blocks.append(import_lines)
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
    # Deferred import: src.utils.materializers depends on this module for the shared
    # dataclasses and neutral parsing helpers (CLAUDE.md's inline-import exception).
    from src.utils.materializers import UnsupportedLanguageError, get_materializer

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
        if language_for_path(entry.path) != 'python':
            unintrospectable.append(entry.path)
            continue
        try:
            existing_signatures = set(extract_existing_signatures(target))
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
                lines.extend(['', *_render_member_body(member, is_method=False).splitlines()])
                continue
            insert_at = _class_insertion_point(lines, member.class_name)
            if insert_at is None:
                continue
            lines[insert_at:insert_at] = ['', *_render_member_body(member, is_method=True).splitlines()]
        target.write_text('\n'.join(lines) + '\n')
        merged.append(target)
    return MergeResult(
        merged_paths=tuple(merged),
        unresolved_signature_conflicts=tuple(unresolved),
        unintrospectable_paths=tuple(unintrospectable),
    )


def generate_tests(project_root: Path, entries: tuple[TestListEntry, ...]) -> TestGenerationResult:
    from src.utils.materializers import UnsupportedLanguageError, get_materializer

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
