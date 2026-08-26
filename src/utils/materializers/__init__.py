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


__all__ = [
    'LanguageMaterializer',
    'PythonMaterializer',
    'TypeScriptMaterializer',
    'UnsupportedLanguageError',
    'get_materializer',
    'sentinel_table',
]
