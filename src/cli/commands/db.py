import asyncio
from argparse import ArgumentParser, Namespace

from rich.table import Table

from src.cli.ui.console import console, print_error, print_info, print_success
from src.utils.database_pool import db_pool
from src.utils.errors import PlanNotFoundError
from src.utils.state_manager import PostgresStateManager


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='db_command', required=True, help='Database commands')

    delete_parser = subparsers.add_parser('delete-plan', help='Delete a plan and all related data')
    delete_parser.add_argument('plan_name', help='Name of the plan to delete')
    delete_parser.add_argument('-f', '--force', action='store_true', help='Skip confirmation prompt')

    subparsers.add_parser('list-plans', help='List all plans stored in the database')


def run(args: Namespace) -> int:
    if args.db_command == 'delete-plan':
        return _run_delete_plan(args)
    elif args.db_command == 'list-plans':
        return _run_list_plans(args)
    else:
        print_error(f'Unknown db command: {args.db_command}')
        return 1


def _run_delete_plan(args: Namespace) -> int:
    plan_name: str = args.plan_name

    if not args.force:
        print_info(
            f'This will permanently delete plan [bold]{plan_name}[/bold] '
            f'and all related data (roadmap, phases, tasks, loops, review sections).'
        )
        response = input('Are you sure? (y/N): ').strip().lower()
        if response not in ('y', 'yes'):
            print_info('Cancelled.')
            return 0

    async def _delete() -> None:
        manager = PostgresStateManager()
        await manager.initialize()
        try:
            await manager.delete_plan(plan_name)
        finally:
            await manager.close()
            await db_pool.close()

    try:
        asyncio.run(_delete())
        print_success(f'Deleted plan [bold]{plan_name}[/bold] and all related data.')
        return 0
    except PlanNotFoundError:
        print_error(f'Plan not found: {plan_name}')
        return 1
    except Exception as e:
        print_error(f'Failed to delete plan: {e}')
        return 1


def _run_list_plans(args: Namespace) -> int:
    async def _list() -> list[str]:
        manager = PostgresStateManager()
        await manager.initialize()
        try:
            return await manager.list_plans()
        finally:
            await manager.close()
            await db_pool.close()

    try:
        plans = asyncio.run(_list())
    except Exception as e:
        print_error(f'Failed to list plans: {e}')
        return 1

    if not plans:
        print_info('No plans found in database.')
        return 0

    table = Table(title='Plans')
    table.add_column('Plan Name', style='cyan')
    for plan in sorted(plans):
        table.add_row(plan)

    console.print(table)
    return 0
