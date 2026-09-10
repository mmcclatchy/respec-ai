import re
from dataclasses import dataclass, field


_SIGNATURE_TAGS = ('internal', 'consequential', 'user-selected', 'async')
_SIGNATURE = re.compile(
    r'^(?:(?P<class_name>[A-Za-z_]\w*)\.)?(?P<member_name>[A-Za-z_]\w*)'
    r'\((?P<params>.*)\)\s*->\s*(?P<return_type>.+)$'
)
# A fully-qualified dotted reference to a non-builtin type, e.g. `kb.models.BestPractice`
# or `pathlib.Path` -- the Skeleton Index convention for any type that needs an import.
# Builtin generics like `list[str]` or `tuple[str, str]` have no dot and never match.
_QUALIFIED_TYPE_REF = re.compile(r'\b(?:[a-zA-Z_]\w*\.)+([A-Z]\w*)\b')


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


def extract_imports_and_bare_text(text: str) -> tuple[str, frozenset[tuple[str, str]]]:
    imports: set[tuple[str, str]] = set()

    def _replace(match: re.Match[str]) -> str:
        class_name = match.group(1)
        module_path = match.group(0)[: -(len(class_name) + 1)]
        imports.add((module_path, class_name))
        return class_name

    bare_text = _QUALIFIED_TYPE_REF.sub(_replace, text)
    return bare_text, frozenset(imports)


def strip_tags(signature: str) -> tuple[str, frozenset[str]]:
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
    """
    Language-neutral structural parse of a tag-stripped signature: class/member name, and
    bare (un-import-extracted) params/return text. The on-disk Skeleton Index grammar is
    uniform across languages, so every LanguageMaterializer.parse_signature starts here.

    This module is the bottom of the skeleton layering: materializers and
    skeleton_generator both import downward from it, which is what keeps them from
    importing each other.
    """
    match = _SIGNATURE.match(remainder)
    if not match:
        raise ValueError(f'Unparseable Skeleton Index signature: {remainder!r}')
    return SkeletonMember(
        class_name=match.group('class_name'),
        member_name=match.group('member_name'),
        params=match.group('params').strip(),
        return_type=match.group('return_type').strip(),
    )
