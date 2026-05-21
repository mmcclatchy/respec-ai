from argparse import Namespace

from src.cli.commands import codex_model, opencode_model
from src.cli.ui.console import console
from src.platform.tui_selector import TuiType


def run_tui_model_setup(tui_type: TuiType, args: Namespace, *, auto_apply: bool = True) -> int:
    """Run TUI-specific model setup during init/sync.

    This orchestration is CLI-owned by design: adapters should not import or
    execute CLI command modules.
    """
    if tui_type == TuiType.CODEX:
        sync_args = Namespace(
            aa_key=getattr(args, 'aa_key', None),
            yes=getattr(args, 'yes', False),
            debug=False,
            no_cache=False,
            include_hidden=False,
            update_codex=False,
            no_update_codex=False,
            reasoning_model=None,
            orchestration_model=None,
            coding_model=None,
            review_model=None,
            project=False,
            no_apply=not auto_apply,
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
            reasoning_model=None,
            orchestration_model=None,
            coding_model=None,
            review_model=None,
            project=False,
        )
        console.print('\n[bold cyan]Configuring OpenCode model tiers...[/bold cyan]\n')
        return opencode_model.run(sync_args)

    return 0
