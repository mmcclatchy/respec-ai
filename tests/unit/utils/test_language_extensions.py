from src.utils.language_extensions import is_frontend_path, language_for_path


def test_a_python_path_resolves_to_python() -> None:
    assert language_for_path('src/kb/client.py') == 'python'


def test_a_typescript_component_path_resolves_to_typescript() -> None:
    assert language_for_path('src/components/LoginForm.tsx') == 'typescript'
    assert language_for_path('src/utils/api.ts') == 'typescript'


def test_an_unrecognized_extension_resolves_to_none() -> None:
    assert language_for_path('README.md') is None


def test_frontend_markup_extensions_are_recognized_even_without_a_materializer() -> None:
    assert is_frontend_path('src/pages/index.astro')
    assert is_frontend_path('src/components/Card.vue')
    assert is_frontend_path('src/components/Card.svelte')
    assert is_frontend_path('src/styles/app.css')


def test_a_backend_path_is_not_classified_as_frontend() -> None:
    assert not is_frontend_path('src/kb/client.py')
