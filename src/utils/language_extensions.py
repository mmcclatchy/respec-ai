from pathlib import Path

# Seeded from the language keys in language_standards.json (F21) -- adding a language's
# materializer later only ever needs an entry here plus a registry entry
# (src/utils/materializers), never a change to this module's callers.
_LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    'python': ('.py',),
    'javascript': ('.js', '.mjs', '.cjs', '.jsx'),
    'typescript': ('.ts', '.tsx', '.mts', '.cts'),
    'java': ('.java',),
    'csharp': ('.cs',),
    'go': ('.go',),
    'rust': ('.rs',),
    'cpp': ('.cpp', '.cc', '.cxx', '.hpp', '.hh'),
    'c': ('.c', '.h'),
    'ruby': ('.rb',),
    'php': ('.php',),
    'swift': ('.swift',),
    'kotlin': ('.kt', '.kts'),
    'scala': ('.scala',),
    'dart': ('.dart',),
    'elixir': ('.ex', '.exs'),
    'lua': ('.lua',),
    'perl': ('.pl', '.pm'),
    'shell': ('.sh', '.bash'),
    'terraform': ('.tf',),
    'powershell': ('.ps1',),
    'haskell': ('.hs',),
    'clojure': ('.clj', '.cljs', '.cljc'),
    'zig': ('.zig',),
    'objective-c': ('.m', '.mm'),
    'r': ('.r', '.R'),
}

# Frontend-flavored extensions with no standalone entry in language_standards.json --
# closest to TypeScript/JavaScript tooling, but carry template markup of their own.
# Recognized for frontend classification (STEP_MODES, F14) even though no materializer
# claims them yet (B1 reports them as unsupported rather than silently mishandling them).
_FRONTEND_MARKUP_EXTENSIONS = ('.vue', '.svelte', '.astro', '.mdx', '.css', '.scss', '.html')

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ext: language for language, extensions in _LANGUAGE_EXTENSIONS.items() for ext in extensions
}

FRONTEND_EXTENSIONS: frozenset[str] = frozenset({'.tsx', '.jsx', *_FRONTEND_MARKUP_EXTENSIONS})


def language_for_path(path: str) -> str | None:
    return EXTENSION_TO_LANGUAGE.get(Path(path).suffix)


def is_frontend_path(path: str) -> bool:
    return Path(path).suffix in FRONTEND_EXTENSIONS
