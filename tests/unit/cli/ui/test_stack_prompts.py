from pytest_mock import MockerFixture

from src.cli.ui.stack_prompts import (
    FRONTEND_FOLLOWUP_FIELDS,
    PER_LANGUAGE_FIELD_ORDER,
    STACK_FIELD_OPTIONS,
    STACK_FIELD_ORDER,
    STACK_MULTI_SELECT_FIELDS,
    _prompt_stack_field,
    prompt_stack_profile,
)
from src.platform.models import LanguageStackProfile, ProjectStack


class TestPromptStackField:
    def test_enter_accepts_detected_default(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('language', 'python')

        assert result == 'python'

    def test_number_selects_option(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '2'

        result = _prompt_stack_field('api_style', 'rest')

        assert result == 'graphql'

    def test_custom_text_returns_custom_value(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'redis'

        result = _prompt_stack_field('database', None)

        assert result == 'redis'

    def test_enter_skips_when_no_detected(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('database', None)

        assert result is None

    def test_invalid_number_reprompts_single_select(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.side_effect = ['99', '1']

        result = _prompt_stack_field('api_style', None)

        assert mock_console.input.call_count == 2
        assert result == STACK_FIELD_OPTIONS['api_style'][0]

    def test_no_options_free_text_only(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '3.13'

        result = _prompt_stack_field('runtime_version', None)

        assert result == '3.13'

    def test_no_options_enter_accepts_detected(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('runtime_version', '3.13')

        assert result == '3.13'

    def test_backend_framework_single_select(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '1'

        result = _prompt_stack_field('backend_framework', None)

        assert result == 'fastapi'

    def test_frontend_framework_single_select(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '1'

        result = _prompt_stack_field('frontend_framework', None)

        assert result == 'react'

    def test_boolean_field_yes_with_detected_true(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('async_runtime', True)

        assert result is True

    def test_boolean_field_no_overrides_detected_true(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'no'

        result = _prompt_stack_field('async_runtime', True)

        assert result is False

    def test_boolean_field_yes_overrides_detected_false(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'yes'

        result = _prompt_stack_field('async_runtime', False)

        assert result is True

    def test_boolean_field_y_accepted(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'y'

        result = _prompt_stack_field('async_runtime', None)

        assert result is True

    def test_boolean_field_n_accepted(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'n'

        result = _prompt_stack_field('async_runtime', None)

        assert result is False

    def test_boolean_field_enter_skips_when_none(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('async_runtime', None)

        assert result is None

    def test_boolean_field_invalid_reprompts(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.side_effect = ['maybe', 'yes']

        result = _prompt_stack_field('async_runtime', True)

        assert mock_console.input.call_count == 2
        assert result is True


class TestMultiSelectFields:
    def test_comma_separated_numbers_selects_multiple(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '1,5'

        result = _prompt_stack_field('database', None)

        assert result == 'postgresql, redis'

    def test_single_number_in_multi_select_field(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '1'

        result = _prompt_stack_field('database', None)

        assert result == 'postgresql'

    def test_comma_separated_custom_text(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = 'postgresql, redis'

        result = _prompt_stack_field('database', None)

        assert result == 'postgresql, redis'

    def test_invalid_number_in_multi_select_reprompts(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.side_effect = ['1,99', '1,2']

        result = _prompt_stack_field('database', None)

        assert mock_console.input.call_count == 2
        assert result == 'postgresql, sqlite'

    def test_enter_accepts_multi_detected_value(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        result = _prompt_stack_field('database', 'postgresql, redis')

        assert result == 'postgresql, redis'

    def test_multi_detected_values_shown_as_detected(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        _prompt_stack_field('database', 'postgresql, redis')

        printed = [str(c) for c in mock_console.print.call_args_list]
        detected_prints = [p for p in printed if '(detected)' in p]
        assert len(detected_prints) == 2

    def test_multi_select_fields_are_configured(self) -> None:
        assert 'language' in STACK_MULTI_SELECT_FIELDS
        assert 'package_manager' in STACK_MULTI_SELECT_FIELDS
        assert 'database' in STACK_MULTI_SELECT_FIELDS
        assert 'backend_framework' not in STACK_MULTI_SELECT_FIELDS
        assert 'frontend_framework' not in STACK_MULTI_SELECT_FIELDS
        assert 'api_style' not in STACK_MULTI_SELECT_FIELDS


class TestPromptStackProfile:
    def test_returns_project_stack(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        detected = ProjectStack(language='python', backend_framework='fastapi')
        result = prompt_stack_profile(detected)

        assert isinstance(result, ProjectStack)
        assert result.language == 'python'
        assert result.languages == ['python']
        assert result.backend_framework == 'fastapi'
        assert result.database is None

    def test_prompts_all_fields(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = ''

        detected = ProjectStack()
        prompt_stack_profile(detected)

        assert mock_console.input.call_count == len(STACK_FIELD_ORDER)

    def test_overrides_detected_values(self, mocker: MockerFixture) -> None:
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        project_responses = {
            'language': '',
            'backend_framework': 'flask',
            'database': 'postgresql',
            'api_style': '',
            'async_runtime': 'no',
            'architecture': '',
        }
        per_language_responses = {
            'package_manager': '',
            'runtime_version': '',
            'type_checker': '',
            'frontend_framework': 'react',
            'css_framework': '',
            'ui_components': '',
        }
        frontend_followup_responses = {'dev_command': '', 'base_url': '', 'storage_state_path': ''}
        mock_console.input.side_effect = (
            [project_responses[f] for f in STACK_FIELD_ORDER]
            + [per_language_responses[f] for f in PER_LANGUAGE_FIELD_ORDER]
            + [frontend_followup_responses[f] for f in FRONTEND_FOLLOWUP_FIELDS]
        )

        detected = ProjectStack(
            language='python',
            backend_framework='fastapi',
            async_runtime=True,
            language_stack={'python': LanguageStackProfile(package_manager='uv')},
        )
        result = prompt_stack_profile(detected)

        assert result.language == 'python'
        assert result.languages == ['python']
        assert result.backend_framework == 'flask'
        assert result.database == 'postgresql'
        assert result.async_runtime is False
        assert result.language_stack['python'].frontend_framework == 'react'
        assert result.language_stack['python'].package_manager == 'uv'

    def test_renaming_detected_javascript_to_typescript_keeps_detected_values(
        self, mocker: MockerFixture
    ) -> None:
        """detect_project_stack names the JS/TS half 'javascript' until tsconfig.json promotes it.
        If the user picks 'typescript' at the language prompt instead, the detected package_manager
        and frontend_framework for that half must not silently vanish."""
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        project_responses = ['typescript', '', '', '', '', '']
        per_language_responses = ['', '', '', '', '', '']
        frontend_followup_responses = ['', '', '']
        mock_console.input.side_effect = project_responses + per_language_responses + frontend_followup_responses

        detected = ProjectStack(
            languages=['javascript'],
            language_stack={
                'javascript': LanguageStackProfile(package_manager='npm', frontend_framework='react')
            },
        )
        result = prompt_stack_profile(detected)

        assert result.languages == ['typescript']
        assert result.language_stack['typescript'].package_manager == 'npm'
        assert result.language_stack['typescript'].frontend_framework == 'react'

    def test_type_checker_options_are_language_specific(self, mocker: MockerFixture) -> None:
        """F25: stack_prompts previously offered only Python type checkers regardless of
        language. A TypeScript language prompt must offer TypeScript's own options."""
        mock_console = mocker.patch('src.cli.ui.stack_prompts.console')
        mock_console.input.return_value = '1'

        result = _prompt_stack_field('type_checker', None, options_override=['tsc'])

        assert result == 'tsc'
