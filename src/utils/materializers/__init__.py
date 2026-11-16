from collections.abc import Iterable

from src.utils.materializers.base import LanguageMaterializer, UnsupportedLanguageError
from src.utils.materializers.python_materializer import PythonMaterializer
from src.utils.materializers.typescript_materializer import TypeScriptMaterializer


# Model: src/platform/tui_adapters/__init__.py's _ADAPTER_MAP -- a literal registry plus
# a fail-loud factory (F27). Adding a language is exactly: a new materializer module +
# one entry here. Nothing else in the codebase should need to change.
_MATERIALIZER_MAP: dict[str, type[LanguageMaterializer]] = {
    'python': PythonMaterializer,
    'typescript': TypeScriptMaterializer,
}

UNMATERIALIZED_LANGUAGE_NOTE = (
    '- No materializer is registered for this language, so no skeleton or test files are generated'
    ' for its paths. Its Skeleton Index and Test List entries are recorded in the design but not'
    ' materialized.\n'
    '- Write them in the same notation as every other language: `<Owner>.<member>(<params>) -> <Result>`'
    ' for a Skeleton Index entry and `<path to a test file>::<observable behavior>` for a Test List'
    " entry, with only the `<params>` and `<Result>` text in this language's syntax. Never write a"
    ' native declaration: the Skeleton Index parser rejects it for every language.\n'
    '- `<Owner>` and `<member>` are each one plain identifier of letters, digits and underscores'
    ' that does not start with a digit: write a qualified owner as its last segment only, and write'
    ' any other character in a name as an underscore.'
)


def get_materializer(language: str | None, path: str = '') -> LanguageMaterializer:
    if language is None or language not in _MATERIALIZER_MAP:
        raise UnsupportedLanguageError(path, language)
    return _MATERIALIZER_MAP[language]()


def sentinel_table() -> dict[str, str]:
    """language -> not_implemented_sentinel, for every registered materializer.

    Lets generated prose (coder.py) name every language's sentinel without hardcoding
    a per-language list that goes stale the moment a new materializer is registered.
    """
    return {language: cls().not_implemented_sentinel for language, cls in _MATERIALIZER_MAP.items()}


def language_authoring_notes(languages: Iterable[str]) -> str:
    sections: list[str] = []
    for language in dict.fromkeys(name.lower() for name in languages):
        materializer = _MATERIALIZER_MAP.get(language)
        notes = materializer().authoring_guidance if materializer else UNMATERIALIZED_LANGUAGE_NOTE
        sections.append(f'#### {language}\n{notes}')
    return '\n\n'.join(sections)


__all__ = [
    'UNMATERIALIZED_LANGUAGE_NOTE',
    'LanguageMaterializer',
    'PythonMaterializer',
    'TypeScriptMaterializer',
    'UnsupportedLanguageError',
    'get_materializer',
    'language_authoring_notes',
    'sentinel_table',
]
