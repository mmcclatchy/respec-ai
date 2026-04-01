from pathlib import Path

SEPARATOR = '═══════════════════════════════════════════════'
UNIVERSAL_FILENAME = 'universal.md'
SKIP_FILES = {'stack.md'}
SKIP_H2_SECTIONS = {'Commands', 'Testing'}

EXAMPLE_PLACEHOLDER = (
    '\n✅ CORRECT:\n'
    '  [Add examples or run /respec-standards to generate]\n'
    '\n❌ WRONG:\n'
    '  [Add examples or run /respec-standards to generate]'
)

VIOLATION_MAP: dict[str, str] = {
    'snake_case': 'Using camelCase for function or variable names.',
    'camelCase': 'Using snake_case for function or variable names.',
    'PascalCase': 'Using lowercase or snake_case for class names.',
    'UPPER_SNAKE_CASE': 'Using lowercase for constant names.',
    'Absolute imports only': 'Using relative imports.',
    'All at file top': 'Using inline imports inside functions.',
    'No inline imports': 'Using inline imports inside functions.',
    'No hardcoded secrets': 'Embedding API keys, passwords, or tokens in source code.',
    'No test logic in production': 'Importing from tests/ in production code.',
    'No production logic in test': 'Importing production helpers into test utilities.',
    'No credentials in source code': 'Embedding API keys, passwords, or tokens in source code.',
    'public APIs only': 'Adding docstrings to obvious getters or simple CRUD functions.',
    'non-obvious business logic only': 'Adding comments to obvious variable declarations or simple calls.',
    'Optional[': 'Using Optional[X] instead of X | None.',
    'Required on all': 'Missing type annotations on function parameters or return values.',
    'No global variables': 'Using mutable global state instead of constants or dependency injection.',
    'nesting': 'Deeply nested code exceeding configured depth limit.',
    'Fail fast': 'Catching exceptions silently without handling or re-raising.',
    'specific exception': 'Using bare except: or catching Exception instead of specific types.',
    'environment variables': 'Hardcoding configuration values instead of using environment variables.',
    'No PII': 'Logging personally identifiable information (names, emails, addresses).',
    'No secrets': 'Logging secrets, tokens, or credentials in log output.',
    'never use var': 'Using var instead of const or let.',
    'Avoid `any`': 'Using the any type instead of proper type annotations.',
    'never ignore returned errors': 'Discarding error return values without checking.',
    'no unwrap()': 'Using unwrap() in production code instead of proper error handling.',
    'Pin versions': 'Using unpinned dependency versions that break reproducible builds.',
}


def is_already_upgraded(content: str) -> bool:
    return SEPARATOR in content


def generate_violations(rules: list[str]) -> list[str]:
    violations: list[str] = []
    for rule in rules:
        for pattern, violation in VIOLATION_MAP.items():
            if pattern.lower() in rule.lower() and violation not in violations:
                violations.append(violation)
    return violations


def upgrade_section(section_name: str, content: str) -> str:
    if is_already_upgraded(content):
        return content

    clean_name = section_name.strip('#').strip()
    block_name = f'MANDATORY {clean_name.upper()} STANDARDS'

    rules = [line.strip() for line in content.strip().splitlines() if line.strip()]
    violations = generate_violations(rules)

    lines = [
        '',
        SEPARATOR,
        block_name,
        SEPARATOR,
    ]
    for rule in rules:
        lines.append(rule)

    if violations:
        lines.append('')
        for v in violations:
            lines.append(f'VIOLATION: {v}')

    lines.append(EXAMPLE_PLACEHOLDER)
    lines.append(SEPARATOR)
    lines.append('')

    return '\n'.join(lines)


def parse_config_sections(content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_h2: str | None = None
    current_h3: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_h3 and current_lines:
            body = '\n'.join(current_lines).strip()
            if body:
                sections.append({
                    'h2': current_h2 or '',
                    'h3': current_h3,
                    'content': body,
                })

    for line in content.splitlines():
        if line.startswith('## ') and not line.startswith('### '):
            flush()
            current_h2 = line[3:].strip()
            current_h3 = None
            current_lines = []
        elif line.startswith('### '):
            flush()
            current_h3 = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return sections


def should_upgrade_section(filename: str, h2: str) -> bool:
    if filename == UNIVERSAL_FILENAME:
        return True
    return h2 == 'Coding Standards'


def upgrade_config_content(filename: str, content: str) -> str:
    sections = parse_config_sections(content)
    result = content

    for section in sections:
        if not should_upgrade_section(filename, section['h2']):
            continue
        if is_already_upgraded(section['content']):
            continue

        upgraded = upgrade_section(section['h3'], section['content'])
        result = result.replace(section['content'], upgraded, 1)

    return result


def upgrade_config_file(path: Path) -> bool:
    content = path.read_text(encoding='utf-8')
    upgraded = upgrade_config_content(path.name, content)

    if upgraded == content:
        return False

    path.write_text(upgraded, encoding='utf-8')
    return True


def find_config_files(project_path: Path, language: str | None = None) -> list[Path]:
    config_dir = project_path / '.respec-ai' / 'config'
    if not config_dir.exists():
        return []

    if language:
        target = config_dir / f'{language}.md'
        return [target] if target.exists() else []

    return [
        f for f in sorted(config_dir.glob('*.md'))
        if f.name not in SKIP_FILES
    ]
