from src.platform.models import LanguageStackProfile, ProjectStack


class TestProjectStack:
    def test_creation_with_all_fields(self) -> None:
        stack = ProjectStack(
            language='python',
            languages=['python'],
            backend_framework='fastapi',
            database='postgresql',
            api_style='rest',
            async_runtime=True,
            architecture='monolith',
            language_stack={
                'python': LanguageStackProfile(
                    frontend_framework='react',
                    package_manager='uv',
                    runtime_version='3.13',
                    type_checker='ty',
                    css_framework='tailwindcss',
                    ui_components='daisyui',
                )
            },
        )
        assert stack.language == 'python'
        assert stack.backend_framework == 'fastapi'
        assert stack.database == 'postgresql'
        assert stack.api_style == 'rest'
        assert stack.async_runtime is True
        assert stack.architecture == 'monolith'
        assert stack.language_stack['python'].frontend_framework == 'react'
        assert stack.language_stack['python'].package_manager == 'uv'
        assert stack.language_stack['python'].runtime_version == '3.13'
        assert stack.language_stack['python'].type_checker == 'ty'
        assert stack.language_stack['python'].css_framework == 'tailwindcss'
        assert stack.language_stack['python'].ui_components == 'daisyui'

    def test_creation_with_partial_fields(self) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        assert stack.language == 'python'
        assert stack.backend_framework == 'fastapi'
        assert stack.database is None
        assert stack.language_stack == {}

    def test_creation_with_no_fields(self) -> None:
        stack = ProjectStack()
        assert stack.language is None
        assert stack.backend_framework is None
        assert stack.language_stack == {}

    def test_exclude_none_serialization(self) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        data = stack.model_dump(exclude_none=True)
        assert data == {'language': 'python', 'backend_framework': 'fastapi', 'language_stack': {}}
        assert 'database' not in data

    def test_immutable(self) -> None:
        stack = ProjectStack(language='python')
        try:
            stack.language = 'go'
            assert False, 'Should have raised'
        except Exception:
            pass


class TestLanguageStackProfile:
    def test_creation_with_new_optional_dev_server_fields(self) -> None:
        profile = LanguageStackProfile(
            frontend_framework='react',
            dev_command='npm run dev',
            base_url='http://localhost:5173',
            storage_state_path='.respec-ai/state/storage-state.json',
        )
        assert profile.frontend_framework == 'react'
        assert profile.dev_command == 'npm run dev'
        assert profile.base_url == 'http://localhost:5173'
        assert profile.storage_state_path == '.respec-ai/state/storage-state.json'

    def test_dev_server_fields_default_to_none(self) -> None:
        profile = LanguageStackProfile()
        assert profile.dev_command is None
        assert profile.base_url is None
        assert profile.storage_state_path is None
