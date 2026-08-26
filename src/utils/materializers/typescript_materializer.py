import re

from src.utils.skeleton_generator import SkeletonIndexEntry, SkeletonMember, TestListEntry, parse_bare_signature

_NAMED_IMPORT = re.compile(r'import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+[\'"][^\'"]+[\'"]')
# Cheap top-level export enumeration -- NOT full introspection (decisions.md
# "Introspection is an optional capability"). It reads exported names only, never
# class-member bodies, which keeps it in the same cost tier as the import scan below
# rather than the deferred TypeScript signature parser.
_EXPORT_FUNCTION = re.compile(r'^export\s+(?:async\s+)?function\s+(\w+)', re.MULTILINE)
_EXPORT_CLASS = re.compile(r'^export\s+class\s+(\w+)', re.MULTILINE)
# Deliberately excludes `export const` -- the Skeleton Index grammar (`name(params) ->
# Return`) has no way to declare a constant, so flagging one as an undesigned addition
# would produce an undeclarable blocker (a const arrow-function component or a shared
# token/route object is normal and often legitimately cross-module). Python's own gate
# has the same blind spot -- _extract_implemented_members only walks
# FunctionDef/AsyncFunctionDef/ClassDef -- so this keeps the two languages symmetric:
# under-detection here, never a blocker the design record cannot express.


def _render_member_body(member: SkeletonMember, is_method: bool) -> str:
    indent = '  ' if is_method else ''
    keyword = 'async ' if 'async' in member.tags else ''
    export = '' if is_method else 'export '
    declare = 'function ' if not is_method else ''
    lines = [
        f'{indent}{export}{keyword}{declare}{member.member_name}({member.params}): {member.return_type} {{'
    ]
    lines.append(f'{indent}  {TypeScriptMaterializer.not_implemented_sentinel}')
    lines.append(f'{indent}}}')
    return '\n'.join(lines)


class TypeScriptMaterializer:
    not_implemented_sentinel = "throw new Error('Not implemented')"
    test_file_suffixes = ('.spec.ts', '.test.ts', '.spec.tsx', '.test.tsx')

    def parse_signature(self, remainder: str) -> SkeletonMember:
        # Dotted-path import inference (skeleton_generator._extract_imports_and_bare_text)
        # is a Python convention -- TypeScript specifiers are relative paths, not dotted
        # module names, so import resolution is deferred rather than guessed at (see
        # decisions.md "Introspection is an optional capability" and the
        # `required_imports` shape note in phase-1-language-seam.md).
        return parse_bare_signature(remainder)

    def render_skeleton_module(self, entry: SkeletonIndexEntry) -> str:
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
            blocks.append(f'export class {class_name} {{\n{method_bodies}\n}}')
        for member in functions:
            blocks.append(_render_member_body(member, is_method=False))

        return '\n\n\n'.join(blocks) + '\n'

    def render_test_module(self, entry: TestListEntry) -> str:
        cases = []
        for test_name in entry.test_names:
            cases.append(
                f"test({test_name!r}, () => {{\n  throw new Error('Not implemented: {test_name}')\n}})"
            )
        return '\n\n\n'.join(cases) + '\n'

    def test_path_convention(self) -> str:
        return 'tests/ or __tests__/ directories -- describe/it blocks with clear descriptions'

    def find_exported_names(self, source: str) -> frozenset[str]:
        names = set(_EXPORT_FUNCTION.findall(source))
        names |= set(_EXPORT_CLASS.findall(source))
        return frozenset(names)

    def references_name(self, source: str, target_name: str, member_name: str, is_method: bool) -> bool:
        imported_names = {
            name.strip().split(' as ')[0].strip()
            for names in _NAMED_IMPORT.findall(source)
            for name in names.split(',')
            if name.strip()
        }
        if target_name not in imported_names:
            return False
        if not is_method:
            return True
        return f'.{member_name}(' in source
