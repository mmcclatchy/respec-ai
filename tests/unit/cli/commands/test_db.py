from argparse import ArgumentParser, Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli.commands import db
from src.utils.errors import PlanNotFoundError


def _make_db_pool_mock() -> MagicMock:
    mock = MagicMock()
    mock.close = AsyncMock()
    return mock


class TestDbCommandArgumentParsing:
    @pytest.fixture
    def parser(self) -> ArgumentParser:
        parser = ArgumentParser()
        db.add_arguments(parser)
        return parser

    def test_delete_plan_requires_plan_name(self, parser: ArgumentParser) -> None:
        with pytest.raises(SystemExit):
            parser.parse_args(['delete-plan'])

    def test_delete_plan_parses_plan_name(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['delete-plan', 'my-plan'])
        assert args.db_command == 'delete-plan'
        assert args.plan_name == 'my-plan'

    def test_delete_plan_force_flag(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['delete-plan', 'my-plan', '--force'])
        assert args.force is True

    def test_delete_plan_no_force_default(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['delete-plan', 'my-plan'])
        assert args.force is False

    def test_list_plans_parses(self, parser: ArgumentParser) -> None:
        args = parser.parse_args(['list-plans'])
        assert args.db_command == 'list-plans'

    def test_requires_subcommand(self, parser: ArgumentParser) -> None:
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestDbDeletePlanCommand:
    @patch('src.cli.commands.db.db_pool', new_callable=_make_db_pool_mock)
    @patch('src.cli.commands.db.PostgresStateManager')
    def test_delete_plan_success(self, mock_manager_cls: MagicMock, mock_pool: MagicMock) -> None:
        mock_manager = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        args = Namespace(db_command='delete-plan', plan_name='my-plan', force=True)
        result = db.run(args)

        assert result == 0
        mock_manager.delete_plan.assert_called_once_with('my-plan')
        mock_manager.close.assert_called_once()

    @patch('src.cli.commands.db.db_pool', new_callable=_make_db_pool_mock)
    @patch('src.cli.commands.db.PostgresStateManager')
    def test_delete_plan_not_found(self, mock_manager_cls: MagicMock, mock_pool: MagicMock) -> None:
        mock_manager = AsyncMock()
        mock_manager.delete_plan.side_effect = PlanNotFoundError('Plan not found: ghost-plan')
        mock_manager_cls.return_value = mock_manager

        args = Namespace(db_command='delete-plan', plan_name='ghost-plan', force=True)
        result = db.run(args)

        assert result == 1

    @patch('src.cli.commands.db.db_pool', new_callable=_make_db_pool_mock)
    @patch('src.cli.commands.db.PostgresStateManager')
    def test_delete_plan_cancelled_by_user(
        self, mock_manager_cls: MagicMock, mock_pool: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr('builtins.input', lambda _: 'n')

        args = Namespace(db_command='delete-plan', plan_name='my-plan', force=False)
        result = db.run(args)

        assert result == 0
        mock_manager_cls.return_value.delete_plan.assert_not_called()


class TestDbListPlansCommand:
    @patch('src.cli.commands.db.db_pool', new_callable=_make_db_pool_mock)
    @patch('src.cli.commands.db.PostgresStateManager')
    def test_list_plans_with_results(self, mock_manager_cls: MagicMock, mock_pool: MagicMock) -> None:
        mock_manager = AsyncMock()
        mock_manager.list_plans.return_value = ['plan-a', 'plan-b']
        mock_manager_cls.return_value = mock_manager

        args = Namespace(db_command='list-plans')
        result = db.run(args)

        assert result == 0
        mock_manager.list_plans.assert_called_once()

    @patch('src.cli.commands.db.db_pool', new_callable=_make_db_pool_mock)
    @patch('src.cli.commands.db.PostgresStateManager')
    def test_list_plans_empty(self, mock_manager_cls: MagicMock, mock_pool: MagicMock) -> None:
        mock_manager = AsyncMock()
        mock_manager.list_plans.return_value = []
        mock_manager_cls.return_value = mock_manager

        args = Namespace(db_command='list-plans')
        result = db.run(args)

        assert result == 0
