from typing import Any

from src.cli.ui.console import console
from src.platform.models import LanguageStackProfile, ProjectStack
from src.platform.tooling_defaults import TYPE_CHECKER_COMMANDS


STACK_FIELD_OPTIONS: dict[str, list[str]] = {
    'language': ['python', 'javascript', 'typescript', 'go', 'rust'],
    'backend_framework': ['fastapi', 'fastmcp', 'flask', 'django', 'express', 'fastify', 'hono'],
    'frontend_framework': ['react', 'next', 'vue', 'svelte', 'angular', 'htmx'],
    'package_manager': ['uv', 'pip', 'npm', 'yarn', 'pnpm', 'cargo'],
    'runtime_version': [],
    'database': ['postgresql', 'sqlite', 'mongodb', 'mysql', 'redis', 'neo4j'],
    'api_style': ['rest', 'graphql', 'grpc', 'mcp'],
    'css_framework': ['tailwindcss', 'bootstrap', 'bulma'],
    'ui_components': ['daisyui', 'shadcn', 'radix', 'headless-ui'],
    'architecture': ['monolith', 'microservices', 'serverless', 'modular-monolith'],
}

# Project-level fields, prompted once regardless of how many languages the project has.
STACK_FIELD_ORDER: list[str] = [
    'language',
    'backend_framework',
    'database',
    'api_style',
    'async_runtime',
    'architecture',
]

STACK_FIELD_SECTIONS: list[tuple[str, list[str]]] = [
    ('Project Languages', ['language']),
    ('Application Frameworks', ['backend_framework', 'api_style', 'async_runtime']),
    ('Data and Architecture', ['database', 'architecture']),
]

# Fields that genuinely vary by language (F2): prompted once per selected language rather than
# once for the whole project, and stored on ProjectStack.language_stack rather than flat.
PER_LANGUAGE_FIELD_ORDER: list[str] = [
    'package_manager',
    'runtime_version',
    'type_checker',
    'frontend_framework',
    'css_framework',
    'ui_components',
]

# Only asked for a language once its frontend_framework is set -- these are what phase 5's
# preflight needs to start a dev server, and asking unconditionally would pester every backend.
FRONTEND_FOLLOWUP_FIELDS: list[str] = ['dev_command', 'base_url', 'storage_state_path']

STACK_MULTI_SELECT_FIELDS: set[str] = {
    'language',
    'package_manager',
    'database',
}


def _build_options_list(options: list[str], detected_values: list[str]) -> list[str]:
    detected_in_options = [v for v in detected_values if v in options]
    rest = [o for o in options if o not in detected_values]
    not_in_options = [v for v in detected_values if v not in options]
    return not_in_options + detected_in_options + rest


def _parse_multi_selection(raw: str, options: list[str], detected_values: list[str]) -> list[str] | None:
    parts = [p.strip() for p in raw.split(',')]

    if all(p.isdigit() for p in parts):
        selected: list[str] = []
        for p in parts:
            index = int(p)
            if index < 1 or index > len(options):
                return None
            selected.append(options[index - 1])
        return selected

    return [p for p in parts if p]


def _prompt_stack_field(
    field_name: str,
    detected_value: str | list[str] | bool | None,
    options_override: list[str] | None = None,
) -> str | list[str] | bool | None:
    label = field_name.replace('_', ' ').title()
    options = list(options_override) if options_override is not None else list(STACK_FIELD_OPTIONS.get(field_name, []))
    multi = field_name in STACK_MULTI_SELECT_FIELDS

    console.print(f'\n  [bold]{label}:[/bold]')

    if isinstance(detected_value, bool):
        default_text = 'yes' if detected_value else 'no'
        prompt = f'  Use async/await patterns? (yes/no) [{default_text}]: '
        while True:
            raw = console.input(prompt).strip().lower()
            if not raw:
                return detected_value
            if raw in ('y', 'yes'):
                return True
            if raw in ('n', 'no'):
                return False
            console.print('  [red]Enter yes or no.[/red]')
    elif detected_value is None and field_name == 'async_runtime':
        prompt = '  Use async/await patterns? (yes/no), or Enter to skip: '
        while True:
            raw = console.input(prompt).strip().lower()
            if not raw:
                return None
            if raw in ('y', 'yes'):
                return True
            if raw in ('n', 'no'):
                return False
            console.print('  [red]Enter yes or no.[/red]')

    detected_values: list[str] = []
    if isinstance(detected_value, str):
        detected_values = [v.strip() for v in detected_value.split(',') if v.strip()]
    elif isinstance(detected_value, list):
        detected_values = [str(v).strip() for v in detected_value if str(v).strip()]

    if options:
        options = _build_options_list(options, detected_values)

        for i, option in enumerate(options, 1):
            suffix = ' (detected)' if option in detected_values else ''
            console.print(f'    {i}. {option}{suffix}')

        if multi:
            number_hint = 'numbers (comma-separated)' if len(options) > 1 else 'number'
        else:
            number_hint = 'number'

        display_default = ', '.join(detected_values) if isinstance(detected_value, list) else detected_value
        if detected_value:
            prompt = f'  Enter {number_hint} or custom value [{display_default}]: '
        else:
            prompt = f'  Enter {number_hint} or custom value, or Enter to skip: '
    else:
        if detected_value:
            prompt = f'  Enter value [{detected_value}]: '
        else:
            prompt = '  Enter value, or Enter to skip: '

    while True:
        raw = console.input(prompt).strip()

        if not raw:
            return detected_value

        if not options:
            return raw

        if multi:
            result = _parse_multi_selection(raw, options, detected_values)
            if result is None:
                console.print(f'  [red]Invalid number. Enter 1-{len(options)}.[/red]')
                continue
            if field_name != 'language':
                return ', '.join(result)
            return result

        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
            console.print(f'  [red]Invalid number. Enter 1-{len(options)}.[/red]')
            continue

        return raw


# javascript/typescript name the same detected package.json half of a project (F2's promotion at
# detection time). If the user renames the language at the prompt (e.g. detection said javascript,
# they pick typescript because tsconfig.json is on the way), the detected profile must follow --
# otherwise every detected value for that half silently vanishes.
_LANGUAGE_PROFILE_ALIASES: dict[str, str] = {'javascript': 'typescript', 'typescript': 'javascript'}


def _detected_profile_for_language(detected: ProjectStack, language: str) -> LanguageStackProfile:
    if language in detected.language_stack:
        return detected.language_stack[language]
    alias = _LANGUAGE_PROFILE_ALIASES.get(language)
    if alias and alias in detected.language_stack:
        return detected.language_stack[alias]
    return LanguageStackProfile()


def _prompt_language_stack(language: str, detected_profile: LanguageStackProfile) -> LanguageStackProfile:
    console.print(f'\n  [bold]{language}[/bold]')

    values: dict[str, Any] = {}
    for field_name in PER_LANGUAGE_FIELD_ORDER:
        options_override = list(TYPE_CHECKER_COMMANDS.get(language, {}).keys()) if field_name == 'type_checker' else None
        detected_value = getattr(detected_profile, field_name)
        values[field_name] = _prompt_stack_field(field_name, detected_value, options_override=options_override)

    if values.get('frontend_framework'):
        for field_name in FRONTEND_FOLLOWUP_FIELDS:
            detected_value = getattr(detected_profile, field_name)
            values[field_name] = _prompt_stack_field(field_name, detected_value)

    return LanguageStackProfile(**values)


def prompt_stack_profile(detected: ProjectStack) -> ProjectStack:
    console.print('\n  [bold cyan]Stack Configuration[/bold cyan]')
    console.print('  Provide values to tune project execution defaults. Press Enter to keep detected values.\n')

    values: dict[str, Any] = {}
    detected_data = detected.model_dump()
    section_for_field = {
        field_name: section_title for section_title, fields in STACK_FIELD_SECTIONS for field_name in fields
    }
    printed_sections: set[str] = set()
    for field_name in STACK_FIELD_ORDER:
        section_title = section_for_field.get(field_name)
        if section_title and section_title not in printed_sections:
            console.print(f'  [bold]{section_title}[/bold]')
            printed_sections.add(section_title)
        if field_name == 'language':
            detected_value = detected.languages or detected_data.get(field_name)
        else:
            detected_value = detected_data.get(field_name)
        values[field_name] = _prompt_stack_field(field_name, detected_value)
        if section_title:
            next_index = STACK_FIELD_ORDER.index(field_name) + 1
            if next_index < len(STACK_FIELD_ORDER):
                next_field = STACK_FIELD_ORDER[next_index]
                if section_for_field.get(next_field) != section_title:
                    console.print()

    selected_language = values.get('language')
    if isinstance(selected_language, list):
        languages = selected_language
    elif isinstance(selected_language, str) and selected_language.strip():
        languages = [selected_language.strip()]
    else:
        languages = []

    language_stack: dict[str, LanguageStackProfile] = {}
    if languages:
        console.print('\n  [bold]Per-Language Configuration[/bold]')
        for language in languages:
            detected_profile = _detected_profile_for_language(detected, language)
            language_stack[language] = _prompt_language_stack(language, detected_profile)

    return ProjectStack(
        language=languages[0] if languages else None,
        languages=languages or None,
        backend_framework=values.get('backend_framework'),
        database=values.get('database'),
        api_style=values.get('api_style'),
        async_runtime=values.get('async_runtime'),
        architecture=values.get('architecture'),
        language_stack=language_stack,
    )
