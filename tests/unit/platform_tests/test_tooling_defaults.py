from pathlib import Path

from src.platform.models import LanguageTooling
from src.platform.tooling_defaults import BUILD_FILE_TO_LANGUAGE, TOOLING_DEFAULTS, detect_project_tooling


class TestToolingDefaults:
    def test_all_four_language_presets_exist(self) -> None:
        expected_languages = {'python', 'javascript', 'go', 'rust'}
        assert set(TOOLING_DEFAULTS.keys()) == expected_languages

    def test_all_presets_are_language_tooling_instances(self) -> None:
        for language, preset in TOOLING_DEFAULTS.items():
            assert isinstance(preset, LanguageTooling), f'{language} preset is not LanguageTooling'

    def test_all_presets_have_populated_fields(self) -> None:
        for language, preset in TOOLING_DEFAULTS.items():
            assert preset.test_runner, f'{language}: test_runner is empty'
            assert preset.test_command, f'{language}: test_command is empty'
            assert preset.coverage_command, f'{language}: coverage_command is empty'
            assert preset.checker, f'{language}: checker is empty'
            assert preset.check_command, f'{language}: check_command is empty'
            assert preset.linter, f'{language}: linter is empty'
            assert preset.lint_command, f'{language}: lint_command is empty'

    def test_python_preset_values(self) -> None:
        python = TOOLING_DEFAULTS['python']
        assert python.test_runner == 'pytest'
        assert python.checker == 'mypy'
        assert python.linter == 'ruff'

    def test_javascript_preset_values(self) -> None:
        js = TOOLING_DEFAULTS['javascript']
        assert js.test_runner == 'vitest'
        assert js.checker == 'tsc'
        assert js.linter == 'eslint'

    def test_go_preset_values(self) -> None:
        go = TOOLING_DEFAULTS['go']
        assert go.test_runner == 'go test'
        assert go.checker == 'go vet'
        assert go.linter == 'golangci-lint'

    def test_rust_preset_values(self) -> None:
        rust = TOOLING_DEFAULTS['rust']
        assert rust.test_runner == 'cargo test'
        assert rust.checker == 'cargo check'
        assert rust.linter == 'clippy'


class TestBuildFileToLanguage:
    def test_expected_build_files_covered(self) -> None:
        expected_files = {'pyproject.toml', 'requirements.txt', 'package.json', 'go.mod', 'Cargo.toml'}
        assert set(BUILD_FILE_TO_LANGUAGE.keys()) == expected_files

    def test_python_build_files(self) -> None:
        assert BUILD_FILE_TO_LANGUAGE['pyproject.toml'] == 'python'
        assert BUILD_FILE_TO_LANGUAGE['requirements.txt'] == 'python'

    def test_javascript_build_file(self) -> None:
        assert BUILD_FILE_TO_LANGUAGE['package.json'] == 'javascript'

    def test_go_build_file(self) -> None:
        assert BUILD_FILE_TO_LANGUAGE['go.mod'] == 'go'

    def test_rust_build_file(self) -> None:
        assert BUILD_FILE_TO_LANGUAGE['Cargo.toml'] == 'rust'

    def test_all_languages_have_defaults(self) -> None:
        for build_file, language in BUILD_FILE_TO_LANGUAGE.items():
            assert language in TOOLING_DEFAULTS, f'{build_file} maps to {language} which has no default preset'


class TestDetectProjectTooling:
    def test_detects_python_from_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]')
        result = detect_project_tooling(tmp_path)
        assert 'python' in result
        assert result['python'].test_runner == 'pytest'

    def test_detects_javascript_from_package_json(self, tmp_path: Path) -> None:
        (tmp_path / 'package.json').write_text('{}')
        result = detect_project_tooling(tmp_path)
        assert 'javascript' in result
        assert result['javascript'].test_runner == 'vitest'

    def test_returns_empty_dict_when_no_build_files(self, tmp_path: Path) -> None:
        result = detect_project_tooling(tmp_path)
        assert result == {}

    def test_no_duplicate_when_multiple_python_build_files(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]')
        (tmp_path / 'requirements.txt').write_text('requests')
        result = detect_project_tooling(tmp_path)
        assert list(result.keys()).count('python') == 1

    def test_detects_multiple_languages(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]')
        (tmp_path / 'package.json').write_text('{}')
        result = detect_project_tooling(tmp_path)
        assert 'python' in result
        assert 'javascript' in result

    def test_returns_language_tooling_instances(self, tmp_path: Path) -> None:
        (tmp_path / 'Cargo.toml').write_text('[package]')
        result = detect_project_tooling(tmp_path)
        assert isinstance(result['rust'], LanguageTooling)
