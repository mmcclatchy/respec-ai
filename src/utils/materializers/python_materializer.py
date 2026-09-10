import ast
from pathlib import Path

from src.utils.skeleton_types import (
    SkeletonIndexEntry,
    SkeletonMember,
    TestListEntry,
    extract_imports_and_bare_text,
    parse_bare_signature,
)


def _parse_python_signature(remainder: str) -> SkeletonMember:
    bare = parse_bare_signature(remainder)
    bare_params, param_imports = extract_imports_and_bare_text(bare.params)
    bare_return_type, return_imports = extract_imports_and_bare_text(bare.return_type)
    return SkeletonMember(
        class_name=bare.class_name,
        member_name=bare.member_name,
        params=bare_params,
        return_type=bare_return_type,
        required_imports=param_imports | return_imports,
    )


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


def _render_signature(qualified_name: str, params: list[ast.arg], returns: ast.expr | None, is_method: bool) -> str:
    if is_method and params and params[0].arg == 'self':
        params = params[1:]
    rendered_params = [f'{a.arg}: {ast.unparse(a.annotation)}' if a.annotation else a.arg for a in params]
    return_type = ast.unparse(returns) if returns else 'None'
    return f'{qualified_name}({", ".join(rendered_params)}) -> {return_type}'


class PythonMaterializer:
    not_implemented_sentinel = 'raise NotImplementedError'
    # Python's test-file convention (test_ prefix, tests/ directory) is already covered
    # by design_conformance.py's language-neutral _TEST_PATH_MARKERS -- no suffix-based
    # convention to add here.
    test_file_suffixes: tuple[str, ...] = ()

    def parse_signature(self, remainder: str) -> SkeletonMember:
        return _parse_python_signature(remainder)

    def render_skeleton_module(self, entry: SkeletonIndexEntry) -> str:
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

    def render_member_body(self, member: SkeletonMember, is_method: bool) -> str:
        return _render_member_body(member, is_method)

    def render_test_module(self, entry: TestListEntry) -> str:
        functions = []
        for test_name in entry.test_names:
            functions.append(f'def {test_name}() -> None:\n    raise AssertionError({test_name!r})')
        return '\n\n\n'.join(functions) + '\n'

    def test_path_convention(self) -> str:
        return 'tests/ directory, mirrors src/ structure -- test_{function}_{scenario} naming'

    def extract_existing_signatures(self, path: Path) -> tuple[str, ...]:
        """
        Full param+return signatures, not bare names -- a same-name divergent signature
        must be visibly different to the reconciliation menu (B2), not silently equal.
        """
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
