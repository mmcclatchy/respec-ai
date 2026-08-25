import ast
from dataclasses import dataclass
from pathlib import Path

from src.utils.skeleton_generator import SkeletonIndexEntry, SkeletonMember, parse_skeleton_index

_TEST_PATH_MARKERS = ('test_', '/tests/', '\\tests\\')


@dataclass(frozen=True)
class RecordedDeviation:
    qualified_name: str
    reason: str


@dataclass(frozen=True)
class ConformanceFinding:
    qualified_name: str
    kind: str
    detail: str


@dataclass(frozen=True)
class ConformanceReport:
    blockers: tuple[ConformanceFinding, ...]
    findings: tuple[ConformanceFinding, ...]
    updated_skeleton_index: str
    new_settled_decisions: str


def _qualified_name(member: SkeletonMember) -> str:
    return f'{member.class_name}.{member.member_name}' if member.class_name else member.member_name


def _param_types(params: str) -> tuple[str | None, ...]:
    types: list[str | None] = []
    for part in params.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            types.append(part.split(':', 1)[1].strip())
        else:
            types.append(None)
    return tuple(types)


@dataclass(frozen=True)
class _ImplementedMember:
    class_name: str | None
    member_name: str
    params: str
    return_type: str


def _render_param(arg: ast.arg) -> str:
    return f'{arg.arg}: {ast.unparse(arg.annotation)}' if arg.annotation else arg.arg


def _extract_implemented_members(path: Path) -> dict[str, _ImplementedMember]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    members: dict[str, _ImplementedMember] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = ', '.join(_render_param(a) for a in node.args.args)
            return_type = ast.unparse(node.returns) if node.returns else 'None'
            members[node.name] = _ImplementedMember(None, node.name, params, return_type)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a for a in item.args.args if a.arg != 'self']
                    params = ', '.join(_render_param(a) for a in args)
                    return_type = ast.unparse(item.returns) if item.returns else 'None'
                    qualified = f'{node.name}.{item.name}'
                    members[qualified] = _ImplementedMember(node.name, item.name, params, return_type)
    return members


def _module_dotted_path(project_root: Path, relative_path: str) -> str:
    return '.'.join(Path(relative_path).with_suffix('').parts)


def _is_test_file(path: Path) -> bool:
    parts = path.parts
    return any(marker.strip('/\\') in parts or path.name.startswith('test_') for marker in _TEST_PATH_MARKERS)


def _is_referenced_from_another_module(
    project_root: Path, owning_module_dotted: str, owning_path: Path, member: SkeletonMember
) -> bool:
    target_name = member.class_name or member.member_name
    for candidate in project_root.rglob('*.py'):
        if candidate.resolve() == owning_path.resolve() or _is_test_file(candidate):
            continue
        try:
            source = candidate.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        imports_target = any(
            isinstance(node, ast.ImportFrom)
            and node.module == owning_module_dotted
            and any(alias.name == target_name for alias in node.names)
            for node in ast.walk(tree)
        )
        if not imports_target:
            continue

        if member.class_name is None:
            return True
        if f'.{member.member_name}(' in source:
            return True
    return False


def _classify_signature_change(
    designed_params: str, designed_return: str, implemented_params: str, implemented_return: str
) -> str:
    designed_types = _param_types(designed_params)
    implemented_types = _param_types(implemented_params)
    designed_raw = f'({designed_params}) -> {designed_return}'
    implemented_raw = f'({implemented_params}) -> {implemented_return}'
    if designed_raw == implemented_raw:
        return 'unchanged'
    if sorted(t or '' for t in designed_types) == sorted(t or '' for t in implemented_types) and (
        designed_return == implemented_return
    ):
        return 'cosmetic'
    return 'protocol'


def classify_conformance(
    project_root: Path,
    skeleton_index_text: str,
    recorded_deviations: tuple[RecordedDeviation, ...] = (),
) -> ConformanceReport:
    designed_entries = parse_skeleton_index(skeleton_index_text)
    deviations_by_name = {d.qualified_name: d.reason for d in recorded_deviations}

    blockers: list[ConformanceFinding] = []
    findings: list[ConformanceFinding] = []
    updated_entries: list[SkeletonIndexEntry] = []
    settled_decision_lines: list[str] = []

    for entry in designed_entries:
        owning_path = project_root / entry.path
        owning_module_dotted = _module_dotted_path(project_root, entry.path)
        implemented_members = _extract_implemented_members(owning_path) if owning_path.exists() else {}

        kept_members: list[SkeletonMember] = []

        for member in entry.members:
            qualified = _qualified_name(member)
            implemented = implemented_members.get(qualified)

            if implemented is None:
                reason = deviations_by_name.get(qualified)
                if reason:
                    findings.append(ConformanceFinding(qualified, 'dropped', reason))
                    settled_decision_lines.append(
                        f'- SD-### | source=implementation | supersedes={qualified} | reason={reason}'
                    )
                else:
                    blockers.append(
                        ConformanceFinding(qualified, 'missing', 'designed member never implemented')
                    )
                    kept_members.append(member)
                continue

            change = _classify_signature_change(
                member.params, member.return_type, implemented.params, implemented.return_type
            )
            if change == 'unchanged':
                kept_members.append(member)
                continue
            if change == 'cosmetic':
                findings.append(ConformanceFinding(qualified, 'cosmetic_changed', 'cosmetic signature change'))
                kept_members.append(member)
                continue

            reason = deviations_by_name.get(qualified)
            if reason:
                findings.append(ConformanceFinding(qualified, 'protocol_changed_recorded', reason))
                new_member = SkeletonMember(
                    class_name=member.class_name,
                    member_name=member.member_name,
                    params=implemented.params,
                    return_type=implemented.return_type,
                    tags=member.tags,
                    required_imports=member.required_imports,
                )
                kept_members.append(new_member)
                settled_decision_lines.append(
                    f'- SD-### | source=implementation | supersedes={qualified}'
                    f'({member.params}) -> {member.return_type} | reason={reason}'
                )
            else:
                blockers.append(
                    ConformanceFinding(qualified, 'protocol_changed_unrecorded', 'signature changed without a recorded reason')
                )
                kept_members.append(member)

        if kept_members:
            updated_entries.append(SkeletonIndexEntry(path=entry.path, members=tuple(kept_members)))

        designed_qualified_names = {_qualified_name(m) for m in entry.members}
        for qualified, implemented in implemented_members.items():
            if qualified in designed_qualified_names:
                continue
            if implemented.member_name.startswith('_'):
                continue
            synthetic_member = SkeletonMember(
                class_name=implemented.class_name,
                member_name=implemented.member_name,
                params=implemented.params,
                return_type=implemented.return_type,
            )
            cross_module = _is_referenced_from_another_module(
                project_root, owning_module_dotted, owning_path, synthetic_member
            )
            if cross_module:
                blockers.append(
                    ConformanceFinding(qualified, 'added_cross_module', 'new public seam not in the design record')
                )
            else:
                findings.append(ConformanceFinding(qualified, 'added_internal', 'module-internal addition'))

    updated_skeleton_index = _render_skeleton_index(updated_entries)
    new_settled_decisions = '\n'.join(settled_decision_lines)

    return ConformanceReport(
        blockers=tuple(blockers),
        findings=tuple(findings),
        updated_skeleton_index=updated_skeleton_index,
        new_settled_decisions=new_settled_decisions,
    )


def _render_member_line(entry_path: str, member: SkeletonMember) -> str:
    qualified = _qualified_name(member)
    tag_suffix = ''.join(f', {tag}' for tag in sorted(member.tags))
    return f'- `{entry_path}` :: {qualified}({member.params}) -> {member.return_type}{tag_suffix}'


def _render_skeleton_index(entries: list[SkeletonIndexEntry]) -> str:
    lines: list[str] = []
    for entry in entries:
        for member in entry.members:
            lines.append(_render_member_line(entry.path, member))
    return '\n'.join(lines)
