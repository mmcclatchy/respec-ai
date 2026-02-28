from src.platform.models import ProjectStack, _render_stack_section


class TestProjectStack:
    def test_creation_with_all_fields(self) -> None:
        stack = ProjectStack(
            language='python',
            backend_framework='fastapi',
            frontend_framework='react',
            package_manager='uv',
            runtime_version='3.13',
            database='postgresql',
            api_style='rest',
            async_runtime=True,
            css_framework='tailwindcss',
            ui_components='daisyui',
            architecture='monolith',
        )
        assert stack.language == 'python'
        assert stack.backend_framework == 'fastapi'
        assert stack.frontend_framework == 'react'
        assert stack.package_manager == 'uv'
        assert stack.runtime_version == '3.13'
        assert stack.database == 'postgresql'
        assert stack.api_style == 'rest'
        assert stack.async_runtime is True
        assert stack.css_framework == 'tailwindcss'
        assert stack.ui_components == 'daisyui'
        assert stack.architecture == 'monolith'

    def test_creation_with_partial_fields(self) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        assert stack.language == 'python'
        assert stack.backend_framework == 'fastapi'
        assert stack.frontend_framework is None
        assert stack.package_manager is None
        assert stack.database is None

    def test_creation_with_no_fields(self) -> None:
        stack = ProjectStack()
        assert stack.language is None
        assert stack.backend_framework is None
        assert stack.frontend_framework is None

    def test_exclude_none_serialization(self) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        data = stack.model_dump(exclude_none=True)
        assert data == {'language': 'python', 'backend_framework': 'fastapi'}
        assert 'database' not in data

    def test_immutable(self) -> None:
        stack = ProjectStack(language='python')
        try:
            stack.language = 'go'  # type: ignore[misc]
            assert False, 'Should have raised'
        except Exception:
            pass


class TestRenderStackSection:
    def test_with_full_stack(self) -> None:
        stack = ProjectStack(
            language='python',
            backend_framework='fastapi',
            frontend_framework='react',
            package_manager='uv',
            runtime_version='3.13',
            api_style='rest',
        )
        result = _render_stack_section(stack)
        assert '**Language**: python' in result
        assert '**Backend Framework**: fastapi' in result
        assert '**Frontend Framework**: react' in result
        assert '**Package Manager**: uv' in result
        assert '**Runtime Version**: 3.13' in result
        assert '**API Style**: rest' in result
        assert 'respec-ai init' in result

    def test_with_partial_stack(self) -> None:
        stack = ProjectStack(language='python', package_manager='uv')
        result = _render_stack_section(stack)
        assert '**Language**: python' in result
        assert '**Package Manager**: uv' in result
        assert 'Backend Framework' not in result
        assert 'Database' not in result

    def test_with_empty_stack(self) -> None:
        stack = ProjectStack()
        result = _render_stack_section(stack)
        assert 'No project stack profile configured' in result
        assert 'respec-ai init' in result
