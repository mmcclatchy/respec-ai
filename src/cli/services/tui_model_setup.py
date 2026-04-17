from argparse import Namespace

from src.cli.commands import codex_model, opencode_model
from src.cli.ui.console import console
from src.platform.tui_selector import TuiType


def run_tui_model_setup(tui_type: TuiType, args: Namespace) -> int:
    """Run TUI-specific model setup during init.

    This orchestration is CLI-owned by design: adapters should not import or
    execute CLI command modules.
    """
    if tui_type == TuiType.CODEX:
        sync_args = Namespace(
            aa_key=getattr(args, 'aa_key', None),
            yes=getattr(args, 'yes', False),
            debug=False,
            no_cache=False,
            reasoning_model=None,
            task_model=None,
        )
        console.print('\n[bold cyan]Configuring Codex model tiers...[/bold cyan]\n')
        return codex_model.run(sync_args)

    if tui_type == TuiType.OPENCODE:
        sync_args = Namespace(
            aa_key=getattr(args, 'aa_key', None),
            exa_key=getattr(args, 'exa_key', None),
            yes=getattr(args, 'yes', False),
            debug=False,
            no_cache=False,
        )
        console.print('\n[bold cyan]Configuring OpenCode model tiers...[/bold cyan]\n')
        return opencode_model.run(sync_args)

    return 0

