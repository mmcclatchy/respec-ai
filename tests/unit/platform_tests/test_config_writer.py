from pathlib import Path

from src.platform.config_writer import write_config_files
from src.platform.models import LanguageTooling, ProjectStack


class TestWriteConfigFiles:
    def test_creates_directory_and_canonical_toml_files(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python', backend_framework='fastapi')
        tooling = {
            'python': LanguageTooling(
                test_runner='pytest',
                test_command='pytest --tb=short -v',
                coverage_command='pytest --cov',
                checker='mypy',
                check_command='mypy src/',
                linter='ruff',
                lint_command='ruff check .',
            )
        }
        written = write_config_files(tmp_path, stack, tooling)

        config_dir = tmp_path / '.respec-ai' / 'config'
        assert config_dir.exists()
        assert (config_dir / 'stack.toml').exists()
        assert (config_dir / 'standards' / 'universal.toml').exists()
        assert (config_dir / 'standards' / 'python.toml').exists()
        assert len(written) == 3

    def test_skips_existing_files(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python')
        tooling = {
            'python': LanguageTooling(
                test_runner='pytest',
                test_command='pytest',
                coverage_command='pytest --cov',
                checker='mypy',
                check_command='mypy .',
                linter='ruff',
                lint_command='ruff check .',
            )
        }
        config_dir = tmp_path / '.respec-ai' / 'config'
        standards_dir = config_dir / 'standards'
        standards_dir.mkdir(parents=True)
        (config_dir / 'stack.toml').write_text(
            'schema_version = 2\n\n[project]\nprimary_language = "python"\nlanguages = ["python"]\n\n'
            '[execution]\nstandards_profile = "opt_in"\nrecommend_preflight = true\n\n'
            '[language.python]\n'
            'runtime_version = ""\npackage_manager = ""\nbackend_framework = ""\n'
            'frontend_framework = ""\ndatabase = ""\napi_style = ""\narchitecture = ""\n'
            'async_runtime = false\ntype_checker = "mypy"\ntest_runner = "pytest"\n'
            'test_command = "pytest"\ncoverage_command = "pytest --cov"\n'
            'type_check_command = "mypy ."\nlint_command = "ruff check ."\n'
        )
        (standards_dir / 'python.toml').write_text(
            'schema_version = 1\nlanguage = "python"\n\n[commands]\n'
            'test = "pytest"\ncoverage = "pytest --cov"\ntype_check = "mypy ."\nlint = "ruff check ."\n\n'
            '[testing]\nframework = "pytest"\nlocation = "tests/"\nnaming = "test_*"\nextras = []\n\n'
            '[rules]\nnaming = ["snake_case"]\nimports = ["absolute imports only"]\n'
            'type_system = ["Required on all function parameters and return values"]\n'
            'documentation = ["Docstrings: public APIs only"]\n'
            'error_handling = ["Fail fast"]\ncode_structure = ["No global variables"]\n'
        )

        written = write_config_files(tmp_path, stack, tooling)

        assert len(written) == 1
        assert written[0].name == 'universal.toml'

    def test_empty_tooling_writes_stack_and_universal_only(self, tmp_path: Path) -> None:
        stack = ProjectStack(language='python')
        written = write_config_files(tmp_path, stack, {})

        config_dir = tmp_path / '.respec-ai' / 'config'
        assert (config_dir / 'stack.toml').exists()
        assert (config_dir / 'standards' / 'universal.toml').exists()
        assert len(written) == 2
