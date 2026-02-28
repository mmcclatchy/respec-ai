from typing import Any

from src.cli.ui.console import console
from src.platform.models import ProjectStack


STACK_FIELD_OPTIONS: dict[str, list[str]] = {
    'language': ['python', 'javascript', 'typescript', 'go', 'rust'],
    'backend_framework': ['fastapi', 'flask', 'django', 'express', 'fastify', 'hono'],
    'frontend_framework': ['react', 'next', 'vue', 'svelte', 'angular', 'htmx'],
    'package_manager': ['uv', 'pip', 'npm', 'yarn', 'pnpm', 'cargo'],
    'runtime_version': [],
    'database': ['postgresql', 'sqlite', 'mongodb', 'mysql', 'redis'],
    'api_style': ['rest', 'graphql', 'grpc'],
    'css_framework': ['tailwindcss', 'bootstrap', 'bulma'],
    'ui_components': ['daisyui', 'shadcn', 'radix', 'headless-ui'],
    'architecture': ['monolith', 'microservices', 'serverless', 'modular-monolith'],
}

STACK_FIELD_ORDER: list[str] = [
    'language',
    'backend_framework',
    'frontend_framework',
    'package_manager',
    'runtime_version',
    'database',
    'api_style',
    'async_runtime',
    'css_framework',
    'ui_components',
    'architecture',
]

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


def _parse_multi_selection(raw: str, options: list[str], detected_values: list[str]) -> str | None:
    parts = [p.strip() for p in raw.split(',')]

    if all(p.isdigit() for p in parts):
        selected: list[str] = []
        for p in parts:
            index = int(p)
            if index < 1 or index > len(options):
                return None
            selected.append(options[index - 1])
        return ', '.join(selected)

    return ', '.join(parts)


def _prompt_stack_field(field_name: str, detected_value: str | bool | None) -> str | bool | None:
    label = field_name.replace('_', ' ').title()
    options = list(STACK_FIELD_OPTIONS.get(field_name, []))
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
        detected_values = [v.strip() for v in detected_value.split(',')]

    if options:
        options = _build_options_list(options, detected_values)

        for i, option in enumerate(options, 1):
            suffix = ' (detected)' if option in detected_values else ''
            console.print(f'    {i}. {option}{suffix}')

        if multi:
            number_hint = 'numbers (comma-separated)' if len(options) > 1 else 'number'
        else:
            number_hint = 'number'

        if detected_value:
            prompt = f'  Enter {number_hint} or custom value [{detected_value}]: '
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
            return result

        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
            console.print(f'  [red]Invalid number. Enter 1-{len(options)}.[/red]')
            continue

        return raw


def prompt_stack_profile(detected: ProjectStack) -> ProjectStack:
    console.print('\n  [bold cyan]Stack Configuration[/bold cyan]')

    values: dict[str, Any] = {}
    detected_data = detected.model_dump()

    for field_name in STACK_FIELD_ORDER:
        detected_value = detected_data.get(field_name)
        values[field_name] = _prompt_stack_field(field_name, detected_value)

    return ProjectStack(**values)
