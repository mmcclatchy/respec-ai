import json
from pathlib import Path

from src.platform.tooling_defaults import detect_project_stack


class TestDetectProjectStackPython:
    def test_detects_python_with_uv(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n\n[tool.uv]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.package_manager == 'uv'

    def test_detects_python_with_pip(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.package_manager == 'pip'

    def test_detects_framework_fastapi(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = ["fastapi>=0.100"]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.framework == 'fastapi'
        assert result.api_style == 'rest'

    def test_detects_framework_flask(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = ["flask>=3.0"]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.framework == 'flask'

    def test_detects_runtime_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\nrequires-python = ">=3.13"\ndependencies = []\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.runtime_version == '3.13'

    def test_handles_malformed_pyproject(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('this is not valid toml {{{')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'


class TestDetectProjectStackJavaScript:
    def test_detects_javascript_npm(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'dependencies': {}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'javascript'
        assert result.package_manager == 'npm'

    def test_detects_typescript(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test'}))
        (tmp_path / 'tsconfig.json').write_text('{}')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'typescript'

    def test_detects_yarn(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test'}))
        (tmp_path / 'yarn.lock').write_text('')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.package_manager == 'yarn'

    def test_detects_pnpm(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test'}))
        (tmp_path / 'pnpm-lock.yaml').write_text('')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.package_manager == 'pnpm'

    def test_detects_react_framework(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'dependencies': {'react': '^18.0'}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.framework == 'react'

    def test_detects_node_runtime_version(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'engines': {'node': '>=22'}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.runtime_version == '22'

    def test_handles_malformed_package_json(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text('not valid json {{{')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'javascript'


class TestDetectProjectStackOther:
    def test_detects_go(self, tmp_path: Path) -> None:
        (tmp_path / 'go.mod').write_text('module example.com/test\ngo 1.22\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'go'
        assert result.package_manager == 'go modules'

    def test_detects_rust(self, tmp_path: Path) -> None:
        (tmp_path / 'Cargo.toml').write_text('[package]\nname = "test"\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'rust'
        assert result.package_manager == 'cargo'

    def test_returns_empty_stack_no_build_files(self, tmp_path: Path) -> None:
        result = detect_project_stack(tmp_path)
        assert result.language is None
        assert result.framework is None
        assert result.model_dump(exclude_none=True) == {}

    def test_python_takes_precedence_over_js(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]\ndependencies = []\n')
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'test'}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
