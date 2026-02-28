from pytest_mock import MockerFixture

from src.cli.ui.stack_prompts import (
    STACK_FIELD_OPTIONS,
    STACK_FIELD_ORDER,
    STACK_MULTI_SELECT_FIELDS,
    _prompt_stack_field,
    prompt_stack_profile,
)
from src.platform.models import ProjectStack


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
        responses = {
            'language': '',
            'backend_framework': 'flask',
            'frontend_framework': 'react',
            'package_manager': '',
            'runtime_version': '',
            'database': 'postgresql',
            'api_style': '',
            'async_runtime': 'no',
            'type_checker': '',
            'css_framework': '',
            'ui_components': '',
            'architecture': '',
        }
        mock_console.input.side_effect = [responses[f] for f in STACK_FIELD_ORDER]

        detected = ProjectStack(
            language='python', backend_framework='fastapi', package_manager='uv', async_runtime=True
        )
        result = prompt_stack_profile(detected)

        assert result.language == 'python'
        assert result.backend_framework == 'flask'
        assert result.frontend_framework == 'react'
        assert result.package_manager == 'uv'
        assert result.database == 'postgresql'
        assert result.async_runtime is False
