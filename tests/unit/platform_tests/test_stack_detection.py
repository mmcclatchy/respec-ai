import json
from pathlib import Path

from src.platform.models import ProjectStack
from src.platform.tooling_defaults import apply_stack_to_tooling, detect_project_stack, TOOLING_DEFAULTS


class TestDetectProjectStackPython:
    def test_detects_python_with_uv(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n\n[tool.uv]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.languages == ['python']
        assert result.package_manager == 'uv'

    def test_detects_python_with_pip(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.package_manager == 'pip'

    def test_detects_backend_framework_fastapi(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = ["fastapi>=0.100"]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.backend_framework == 'fastapi'
        assert result.api_style == 'rest'
        assert result.async_runtime is True

    def test_detects_backend_framework_flask(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = ["flask>=3.0"]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.backend_framework == 'flask'
        assert result.async_runtime is False

    def test_detects_backend_framework_fastmcp(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = ["fastmcp>=2.0"]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.backend_framework == 'fastmcp'
        assert result.api_style == 'mcp'
        assert result.async_runtime is True

    def test_detects_runtime_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\nrequires-python = ">=3.13"\ndependencies = []\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.runtime_version == '3.13'

    def test_detects_type_checker_ty(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n\n[tool.ty]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.type_checker == 'ty'

    def test_detects_type_checker_mypy(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n\n[tool.mypy]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.type_checker == 'mypy'

    def test_detects_type_checker_pyright(self, tmp_path: Path) -> None:
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n\n[tool.pyright]\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.type_checker == 'pyright'

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
        assert result.languages == ['javascript']
        assert result.package_manager == 'npm'

    def test_detects_typescript(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test'}))
        (tmp_path / 'tsconfig.json').write_text('{}')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'typescript'
        assert result.languages == ['typescript']

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

    def test_detects_frontend_framework_react(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'dependencies': {'react': '^18.0'}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.frontend_framework == 'react'
        assert result.backend_framework is None

    def test_detects_backend_framework_express(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'dependencies': {'express': '^4.0'}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.backend_framework == 'express'
        assert result.api_style == 'rest'
        assert result.async_runtime is True

    def test_detects_both_frameworks(self, tmp_path: Path) -> None:
        package_json = tmp_path / 'package.json'
        package_json.write_text(json.dumps({'name': 'test', 'dependencies': {'express': '^4.0', 'react': '^18.0'}}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.backend_framework == 'express'
        assert result.frontend_framework == 'react'
        assert result.async_runtime is True

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
        assert result.backend_framework is None
        assert result.frontend_framework is None
        assert result.model_dump(exclude_none=True) == {}

    def test_python_takes_precedence_over_js(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]\ndependencies = []\n')
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'test'}))
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.languages == ['python', 'javascript']

    def test_detects_multilanguage_project_stack(self, tmp_path: Path) -> None:
        (tmp_path / 'pyproject.toml').write_text('[project]\ndependencies = []\n')
        (tmp_path / 'go.mod').write_text('module example.com/test\ngo 1.22\n')
        result = detect_project_stack(tmp_path)
        assert result is not None
        assert result.language == 'python'
        assert result.languages == ['python', 'go']


class TestApplyStackToTooling:
    def test_updates_checker_to_ty(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python', type_checker='ty')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].checker == 'ty'
        assert result['python'].check_command == 'ty check'

    def test_updates_checker_to_mypy(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python', type_checker='mypy')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].checker == 'mypy'
        assert result['python'].check_command == 'mypy src/ --exclude tests/'

    def test_updates_checker_to_pyright(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python', type_checker='pyright')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].checker == 'pyright'
        assert result['python'].check_command == 'pyright'

    def test_updates_checker_to_pytype(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python', type_checker='pytype')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].checker == 'pytype'
        assert result['python'].check_command == 'pytype src/'

    def test_preserves_other_tooling_fields(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python', type_checker='ty')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].test_runner == 'pytest'
        assert result['python'].linter == 'ruff'

    def test_no_change_when_no_type_checker(self) -> None:
        tooling = {'python': TOOLING_DEFAULTS['python']}
        stack = ProjectStack(language='python')
        result = apply_stack_to_tooling(tooling, stack)
        assert result['python'].checker == 'mypy'

    def test_no_change_when_language_not_in_tooling(self) -> None:
        tooling = {'javascript': TOOLING_DEFAULTS['javascript']}
        stack = ProjectStack(language='python', type_checker='ty')
        result = apply_stack_to_tooling(tooling, stack)
        assert result == tooling
