from pathlib import Path

import pytest

from src.cli.standards.upgrader import (
    EXAMPLE_PLACEHOLDER,
    SEPARATOR,
    find_config_files,
    generate_violations,
    is_already_upgraded,
    parse_config_sections,
    should_upgrade_section,
    upgrade_config_content,
    upgrade_config_file,
    upgrade_section,
)


class TestIsAlreadyUpgraded:
    def test_detects_separator(self) -> None:
        assert is_already_upgraded(f'some text\n{SEPARATOR}\nmore text')

    def test_returns_false_for_plain_content(self) -> None:
        assert not is_already_upgraded('- snake_case\n- PascalCase')


class TestGenerateViolations:
    def test_generates_snake_case_violation(self) -> None:
        violations = generate_violations(['- Variables/functions: snake_case'])
        assert any('camelCase' in v for v in violations)

    def test_generates_pascal_case_violation(self) -> None:
        violations = generate_violations(['- Classes: PascalCase'])
        assert any('lowercase' in v.lower() or 'snake_case' in v for v in violations)

    def test_generates_secrets_violation(self) -> None:
        violations = generate_violations(['- No hardcoded secrets'])
        assert any('API keys' in v or 'passwords' in v for v in violations)

    def test_generates_inline_import_violation(self) -> None:
        violations = generate_violations(['- All at file top'])
        assert any('inline' in v.lower() for v in violations)

    def test_no_duplicates(self) -> None:
        violations = generate_violations([
            '- No inline imports',
            '- All at file top',
        ])
        assert len(violations) == len(set(violations))

    def test_returns_empty_for_unknown_rules(self) -> None:
        violations = generate_violations(['- Use tabs for indentation'])
        assert violations == []

    def test_generates_optional_violation(self) -> None:
        violations = generate_violations(['- Use `X | None` not `Optional[X]`'])
        assert any('Optional' in v for v in violations)

    def test_generates_type_hint_required_violation(self) -> None:
        violations = generate_violations(['- Required on all function parameters'])
        assert any('Missing type annotations' in v for v in violations)

    def test_generates_fail_fast_violation(self) -> None:
        violations = generate_violations(['- Fail fast — validate inputs early'])
        assert any('silently' in v.lower() or 'catching' in v.lower() for v in violations)

    def test_generates_global_variable_violation(self) -> None:
        violations = generate_violations(['- No global variables except constants'])
        assert any('global' in v.lower() for v in violations)


class TestUpgradeSection:
    def test_wraps_in_mandatory_block(self) -> None:
        result = upgrade_section('### Naming', '- snake_case\n- PascalCase')
        assert SEPARATOR in result
        assert 'MANDATORY NAMING STANDARDS' in result
        assert '- snake_case' in result
        assert '- PascalCase' in result

    def test_includes_violations(self) -> None:
        result = upgrade_section('### Naming', '- Variables: snake_case')
        assert 'VIOLATION:' in result

    def test_includes_example_placeholder(self) -> None:
        result = upgrade_section('### Naming', '- snake_case')
        assert '✅ CORRECT:' in result
        assert '❌ WRONG:' in result
        assert '/respec-standards' in result

    def test_skips_already_upgraded(self) -> None:
        content = f'{SEPARATOR}\nMANDATORY\n{SEPARATOR}'
        result = upgrade_section('### Test', content)
        assert result == content


class TestParseConfigSections:
    def test_parses_h2_and_h3(self) -> None:
        content = '## Coding Standards\n\n### Naming\n- snake_case\n\n### Imports\n- absolute only\n'
        sections = parse_config_sections(content)
        assert len(sections) == 2
        assert sections[0]['h2'] == 'Coding Standards'
        assert sections[0]['h3'] == 'Naming'
        assert 'snake_case' in sections[0]['content']
        assert sections[1]['h3'] == 'Imports'

    def test_ignores_h2_without_h3(self) -> None:
        content = '## Commands\n\n- **Test**: `pytest`\n'
        sections = parse_config_sections(content)
        assert len(sections) == 0

    def test_handles_multiple_h2_groups(self) -> None:
        content = '## Security\n\n### Secrets\n- no hardcoded\n\n## Imports\n\n### Organization\n- top of file\n'
        sections = parse_config_sections(content)
        assert len(sections) == 2
        assert sections[0]['h2'] == 'Security'
        assert sections[1]['h2'] == 'Imports'


class TestShouldUpgradeSection:
    def test_universal_upgrades_all_sections(self) -> None:
        assert should_upgrade_section('universal.md', 'Security')
        assert should_upgrade_section('universal.md', 'Imports')
        assert should_upgrade_section('universal.md', 'Code Separation')

    def test_language_upgrades_coding_standards_only(self) -> None:
        assert should_upgrade_section('python.md', 'Coding Standards')
        assert not should_upgrade_section('python.md', 'Commands')
        assert not should_upgrade_section('python.md', 'Testing')


class TestUpgradeConfigContent:
    def test_upgrades_coding_standards_sections(self) -> None:
        content = (
            '# Python\n\n'
            '## Commands\n\n- **Test**: `pytest`\n\n'
            '## Coding Standards\n\n'
            '### Naming\n- snake_case\n'
        )
        result = upgrade_config_content('python.md', content)
        assert SEPARATOR in result
        assert 'MANDATORY NAMING STANDARDS' in result
        assert '- **Test**: `pytest`' in result

    def test_skips_commands_section(self) -> None:
        content = '## Commands\n\n### Test\n- pytest\n'
        result = upgrade_config_content('python.md', content)
        assert SEPARATOR not in result

    def test_upgrades_all_universal_sections(self) -> None:
        content = '## Security\n\n### Secrets\n- No hardcoded secrets\n'
        result = upgrade_config_content('universal.md', content)
        assert SEPARATOR in result
        assert 'MANDATORY' in result

    def test_idempotent(self) -> None:
        content = '## Coding Standards\n\n### Naming\n- snake_case\n'
        first = upgrade_config_content('python.md', content)
        second = upgrade_config_content('python.md', first)
        assert first == second


class TestUpgradeConfigFile:
    def test_upgrades_file_in_place(self, tmp_path: Path) -> None:
        config = tmp_path / 'python.md'
        config.write_text('## Coding Standards\n\n### Naming\n- snake_case\n')

        changed = upgrade_config_file(config)

        assert changed is True
        result = config.read_text()
        assert SEPARATOR in result
        assert 'MANDATORY NAMING STANDARDS' in result

    def test_returns_false_if_no_changes(self, tmp_path: Path) -> None:
        config = tmp_path / 'python.md'
        config.write_text('## Commands\n\n- **Test**: `pytest`\n')

        changed = upgrade_config_file(config)

        assert changed is False


class TestFindConfigFiles:
    def test_finds_all_config_files_except_stack(self, tmp_path: Path) -> None:
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)
        (config_dir / 'universal.md').write_text('content')
        (config_dir / 'python.md').write_text('content')
        (config_dir / 'stack.md').write_text('content')

        files = find_config_files(tmp_path)

        names = [f.name for f in files]
        assert 'universal.md' in names
        assert 'python.md' in names
        assert 'stack.md' not in names

    def test_finds_specific_language(self, tmp_path: Path) -> None:
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)
        (config_dir / 'python.md').write_text('content')
        (config_dir / 'javascript.md').write_text('content')

        files = find_config_files(tmp_path, 'python')

        assert len(files) == 1
        assert files[0].name == 'python.md'

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        assert find_config_files(tmp_path) == []

    def test_returns_empty_for_missing_language(self, tmp_path: Path) -> None:
        config_dir = tmp_path / '.respec-ai' / 'config'
        config_dir.mkdir(parents=True)

        assert find_config_files(tmp_path, 'rust') == []
