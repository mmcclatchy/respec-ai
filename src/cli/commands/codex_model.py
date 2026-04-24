import json
import os
import re
import select
import subprocess
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, cast

from rich.table import Table

from src.cli.config.global_config import GLOBAL_MODELS_PATH, load_api_key, save_api_key, save_global_models
from src.cli.ui.console import console, print_error, print_info, print_warning


from src.cli.commands import regenerate


_AA_MODELS_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'
_CACHE_DIR = Path.home() / '.config' / 'respec-ai' / 'cache'
_CACHE_TTL_SECONDS = 12 * 60 * 60
_REASONING_INDEX = 'artificial_analysis_intelligence_index'
_CODING_INDEX = 'artificial_analysis_coding_index'
_CODEX_APP_SERVER_CMD = ['codex', 'app-server', '--listen', 'stdio://']
_CODEX_UPDATE_CMD = ['npm', 'install', '-g', '@openai/codex']
_CODEX_DISCOVERY_CACHE_KEY = 'codex_models_discovered'
_CODEX_DISCOVERY_TIMEOUT_SECONDS = 15
_CODEX_DISCOVERY_PAGE_LIMIT = 100


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--aa-key',
        help='Artificial Analysis API key (overrides ARTIFICIAL_ANALYSIS_API_KEY env var)',
    )
    parser.add_argument('--debug', action='store_true', help='Print debug info for API calls')
    parser.add_argument('--no-cache', action='store_true', help='Bypass cached API responses')
    parser.add_argument(
        '--include-hidden',
        action='store_true',
        help='Include hidden models that do not appear in the default Codex picker',
    )
    update_group = parser.add_mutually_exclusive_group()
    update_group.add_argument(
        '--update-codex',
        action='store_true',
        help='Update Codex CLI with npm before discovering models',
    )
    update_group.add_argument(
        '--no-update-codex',
        action='store_true',
        help='Skip the Codex CLI update prompt before discovering models',
    )
    parser.add_argument('--reasoning-model', help='Set reasoning model directly')
    parser.add_argument('--orchestration-model', help='Set orchestration model directly')
    parser.add_argument('--task-model', dest='orchestration_model', help='Alias for --orchestration-model')
    parser.add_argument('--coding-model', help='Set coding model directly')
    parser.add_argument('--review-model', help='Set review model directly')
    parser.add_argument(
        '--no-apply',
        action='store_true',
        help='Save global model mapping only (skip forced regenerate for current codex project)',
    )


def run(args: Namespace) -> int:
    direct_reasoning = getattr(args, 'reasoning_model', None)
    direct_orchestration = getattr(args, 'orchestration_model', None) or getattr(args, 'task_model', None)
    direct_coding = getattr(args, 'coding_model', None)
    direct_review = getattr(args, 'review_model', None)
    if direct_reasoning or direct_orchestration or direct_coding or direct_review:
        mapping = _build_direct_mapping(direct_reasoning, direct_orchestration, direct_coding, direct_review)
        if mapping is None:
            return 1
        _warn_if_unknown_mapping(mapping)
        return _save_and_apply(mapping, no_apply=bool(getattr(args, 'no_apply', False)))

    aa_key = (
        getattr(args, 'aa_key', None)
        or os.environ.get('ARTIFICIAL_ANALYSIS_API_KEY', '')
        or load_api_key('artificial_analysis')
        or ''
    )
    if aa_key and getattr(args, 'aa_key', None):
        save_api_key('artificial_analysis', aa_key)
    if getattr(args, 'no_cache', False):
        _clear_cache()
    debug = getattr(args, 'debug', False)
    include_hidden = bool(getattr(args, 'include_hidden', False))

    if not _maybe_update_codex_cli(args):
        return 1

    discovered = _discover_codex_models(include_hidden=include_hidden, debug=debug)
    if not discovered:
        return 1

    models = [entry['id'] for entry in discovered]

    console.print('Provider: [cyan]codex[/cyan]')
    console.print(f'Available models: {", ".join(models)}\n')

    if aa_key:
        print_info('Fetching benchmark data from Artificial Analysis...')
        aa_data = _fetch_aa_data(aa_key, debug=debug)
        if aa_data:
            _display_aa_table(discovered, aa_data)
    else:
        print_info('ARTIFICIAL_ANALYSIS_API_KEY not set — skipping benchmark context.')

    mapping = _interactive_select_models(discovered)
    if mapping is None:
        print_warning('Mapping not saved')
        return 1

    _warn_if_unknown_mapping(mapping, known_models=set(models))
    return _save_and_apply(mapping, no_apply=bool(getattr(args, 'no_apply', False)))


def _build_direct_mapping(
    reasoning: str | None,
    orchestration: str | None,
    coding: str | None,
    review: str | None,
) -> dict[str, str] | None:
    reasoning_value = str(reasoning or '').strip()
    orchestration_value = str(orchestration or '').strip()
    coding_value = str(coding or '').strip()
    review_value = str(review or '').strip()
    if not reasoning_value or not orchestration_value or not coding_value or not review_value:
        print_warning(
            'Direct Codex model setup requires --reasoning-model, --orchestration-model '
            '(or --task-model), --coding-model, and --review-model'
        )
        return None
    return {
        'reasoning': reasoning_value,
        'orchestration': orchestration_value,
        'coding': coding_value,
        'review': review_value,
    }


def _save_and_apply(mapping: dict[str, str], *, no_apply: bool) -> int:
    save_global_models(mapping, provider='codex')
    console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
    return _auto_apply_to_current_project(no_apply=no_apply)


def _auto_apply_to_current_project(*, no_apply: bool) -> int:
    if no_apply:
        print_info("Auto-apply skipped (--no-apply). Run 'respec-ai regenerate --force' when ready.")
        return 0

    config_path = Path.cwd() / '.respec-ai' / 'config.json'
    if not config_path.exists():
        print_info('Auto-apply skipped: .respec-ai/config.json not found in current directory.')
        print_info("Run 'respec-ai regenerate --force' inside an initialized Codex project.")
        return 0

    try:
        json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        print_warning(f'Auto-apply skipped: could not read project config ({e}).')
        print_info("Run 'respec-ai regenerate --force' after fixing .respec-ai/config.json.")
        return 0

    print_info('Applying saved Codex model tiers to detected project TUI artifacts (forced regenerate)...')
    if _run_forced_regenerate() != 0:
        print_warning('Auto-apply failed: forced regenerate returned non-zero exit code.')
        return 1
    print_info('Applied saved Codex model tiers to detected project TUI artifacts.')
    return 0


def _run_forced_regenerate() -> int:
    return regenerate.run(Namespace(force=True))


def _maybe_update_codex_cli(args: Namespace) -> bool:
    if bool(getattr(args, 'no_update_codex', False)):
        print_info('Codex CLI update skipped (--no-update-codex).')
        return True

    should_update = bool(getattr(args, 'update_codex', False))
    if not should_update:
        response = (
            console.input(
                'Update Codex CLI before discovering models? [dim]Runs: npm install -g @openai/codex[/dim] [y/N] '
            )
            .strip()
            .lower()
        )
        should_update = response in ('y', 'yes')

    if not should_update:
        print_info('Codex CLI update skipped.')
        return True

    print_info('Updating Codex CLI with npm install -g @openai/codex...')
    try:
        result = subprocess.run(_CODEX_UPDATE_CMD)
    except (FileNotFoundError, OSError) as exc:
        print_error(f'Could not update Codex CLI: {exc}')
        return False

    if result.returncode != 0:
        print_error(f'Codex CLI update failed with exit code {result.returncode}')
        return False

    print_info('Codex CLI update completed.')
    return True


def _warn_if_unknown_mapping(mapping: dict[str, str], known_models: set[str] | None = None) -> None:
    known = known_models if known_models is not None else set(_cached_discovered_model_ids())
    if not known:
        return
    for tier, model in mapping.items():
        if model not in known:
            print_warning(f'{tier.title()} model "{model}" is not in the discovered Codex model list; saving anyway')


def _read_cache(name: str) -> dict | list | None:
    path = _CACHE_DIR / f'{name}.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if time.time() - data.get('_cached_at', 0) > _CACHE_TTL_SECONDS:
            return None
        payload = data.get('payload')
        if isinstance(payload, (dict, list)):
            return payload
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(name: str, payload: object) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {'_cached_at': time.time(), 'payload': payload}
        (_CACHE_DIR / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')
    except OSError:
        pass


def _clear_cache() -> None:
    if not _CACHE_DIR.exists():
        return
    for f in _CACHE_DIR.glob('*.json'):
        f.unlink(missing_ok=True)


def _cached_discovered_model_ids() -> list[str]:
    cached = _read_cache(_CODEX_DISCOVERY_CACHE_KEY)
    entries = _normalize_discovered_models(cached)
    return [entry['id'] for entry in entries]


def _discover_codex_models(*, include_hidden: bool, debug: bool = False) -> list[dict[str, Any]]:
    discovered_all: list[dict[str, Any]] = []
    try:
        discovered_all = _fetch_codex_models_live(debug=debug)
        _write_cache(_CODEX_DISCOVERY_CACHE_KEY, discovered_all)
    except RuntimeError as exc:
        cached = _read_cache(_CODEX_DISCOVERY_CACHE_KEY)
        discovered_all = _normalize_discovered_models(cached)
        if discovered_all:
            print_warning(f'Live Codex model discovery failed ({exc}) — using cached model list')
        else:
            print_error(f'Could not discover Codex models: {exc}')
            print_info("Ensure Codex is installed and authenticated, then rerun 'respec-ai models codex'.")
            return []

    filtered = [entry for entry in discovered_all if include_hidden or not entry['hidden']]
    if not filtered:
        if include_hidden:
            print_error('Codex model discovery returned no models.')
            return []
        print_error('No non-hidden Codex models discovered. Retry with --include-hidden.')
        return []

    return filtered


def _fetch_codex_models_live(*, debug: bool = False) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen_cursors: set[str] = set()
    cursor: str | None = None

    while True:
        page = _request_codex_model_page(cursor=cursor, debug=debug)
        data = page.get('data')
        if not isinstance(data, list):
            raise RuntimeError('Codex app-server returned malformed model/list payload')
        for item in data:
            if isinstance(item, dict):
                collected.append(item)

        next_cursor = page.get('nextCursor')
        if not next_cursor:
            break
        if not isinstance(next_cursor, str):
            raise RuntimeError('Codex app-server returned non-string nextCursor')
        if next_cursor in seen_cursors:
            raise RuntimeError('Codex app-server returned a repeated pagination cursor')
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    models = _normalize_discovered_models(collected)
    if not models:
        raise RuntimeError('Codex app-server returned an empty model list')

    if debug:
        console.print(f'[dim]  Codex discovered models: {len(models)}[/dim]')

    return models


def _request_codex_model_page(*, cursor: str | None, debug: bool = False) -> dict[str, Any]:
    try:
        process = subprocess.Popen(
            _CODEX_APP_SERVER_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, OSError) as exc:
        raise RuntimeError(f'failed to start Codex app-server: {exc}') from exc

    try:
        _write_json_line(
            process,
            {
                'method': 'initialize',
                'id': 0,
                'params': {
                    'clientInfo': {'name': 'respec-ai', 'title': 'respec-ai', 'version': '0.0.0'},
                    'capabilities': None,
                },
            },
        )
        _write_json_line(process, {'method': 'initialized'})

        params: dict[str, Any] = {'includeHidden': True, 'limit': _CODEX_DISCOVERY_PAGE_LIMIT}
        if cursor:
            params['cursor'] = cursor
        _write_json_line(process, {'method': 'model/list', 'id': 1, 'params': params})

        result = _read_response_for_id(process, request_id=1, timeout_seconds=_CODEX_DISCOVERY_TIMEOUT_SECONDS)
        if debug:
            count = len(result.get('data', [])) if isinstance(result.get('data'), list) else 0
            console.print(f'[dim]  Codex model/list page received: {count} models[/dim]')
        return result
    finally:
        _shutdown_process(process)


def _write_json_line(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError('Codex app-server stdin unavailable')
    try:
        process.stdin.write(json.dumps(payload) + '\n')
        process.stdin.flush()
    except OSError as exc:
        raise RuntimeError(f'failed writing to Codex app-server stdin: {exc}') from exc


def _read_response_for_id(
    process: subprocess.Popen[str],
    *,
    request_id: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        message = _read_next_json_message(process, deadline)
        if message is None:
            if process.poll() is not None:
                break
            continue

        if message.get('id') != request_id:
            continue

        if 'error' in message:
            raise RuntimeError(f'Codex app-server returned error: {message["error"]}')

        result = message.get('result')
        if isinstance(result, dict):
            return result
        raise RuntimeError('Codex app-server returned a non-object result payload')

    stderr_tail = _read_stderr_tail(process)
    if stderr_tail:
        raise RuntimeError(f'Codex app-server response timeout/failure: {stderr_tail}')
    raise RuntimeError('timed out waiting for Codex app-server response')


def _read_next_json_message(process: subprocess.Popen[str], deadline: float) -> dict[str, Any] | None:
    if process.stdout is None:
        return None

    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            ready, _, _ = select.select([process.stdout], [], [], remaining)
        except (OSError, ValueError):
            return None
        if not ready:
            return None

        line = process.stdout.readline()
        if line == '':
            return None

        raw = line.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


def _read_stderr_tail(process: subprocess.Popen[str]) -> str:
    if process.stderr is None:
        return ''
    try:
        text = process.stderr.read() or ''
    except OSError:
        return ''
    return text.strip()[:300]


def _shutdown_process(process: subprocess.Popen[str]) -> None:
    if process.stdin is not None and not process.stdin.closed:
        try:
            process.stdin.close()
        except OSError:
            pass

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)


def _normalize_discovered_models(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        raw_data = cast(dict[str, Any], raw)

        model_id = str(raw_data.get('id') or raw_data.get('model') or '').strip()
        if not model_id or model_id in seen_ids:
            continue

        display_name = str(raw_data.get('displayName') or raw_data.get('display_name') or model_id).strip() or model_id
        description = str(raw_data.get('description') or '').strip()
        hidden = bool(raw_data.get('hidden', False))
        is_default = bool(raw_data.get('isDefault', raw_data.get('is_default', False)))

        normalized.append(
            {
                'id': model_id,
                'display_name': display_name,
                'description': description,
                'hidden': hidden,
                'is_default': is_default,
            }
        )
        seen_ids.add(model_id)

    return normalized


def _fetch_aa_data(aa_key: str, *, debug: bool = False) -> dict[str, dict[str, float]]:
    cached = _read_cache('aa_data_codex')
    if isinstance(cached, dict):
        if debug:
            console.print(f'[dim]  AA using cached data ({len(cached)} models)[/dim]')
        return cached

    req = urllib.request.Request(
        _AA_MODELS_URL,
        headers={'x-api-key': aa_key, 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result: dict[str, dict[str, float]] = {}
        all_fields = {_REASONING_INDEX, _CODING_INDEX}
        models_list = data if isinstance(data, list) else data.get('models', data.get('data', []))
        for model in models_list:
            name = (model.get('name') or model.get('slug') or '').lower()
            if not name:
                continue
            evals = model.get('evaluations') or {}
            scores: dict[str, float] = {}
            for field in all_fields:
                val = evals.get(field)
                if val is not None:
                    scores[field] = float(val)
            if scores:
                result[name] = scores
        _write_cache('aa_data_codex', result)
        return result
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        print_warning('Could not fetch Artificial Analysis data — skipping benchmark context')
        return {}


def _normalize_name(name: str) -> str:
    lowered = name.lower().replace('-', ' ').replace('_', ' ')
    return re.sub(r'\s+', ' ', lowered).strip()


def _find_aa_match(model_id: str, aa_data: dict[str, dict[str, float]], aliases: set[str] | None = None) -> str:
    model_norm = _normalize_name(model_id)
    candidate_aliases = {model_norm}
    if aliases:
        candidate_aliases.update(_normalize_name(alias) for alias in aliases)

    for key in aa_data:
        norm_key = _normalize_name(key)
        if norm_key in candidate_aliases:
            return key
    for key in aa_data:
        norm_key = _normalize_name(key)
        if any(alias in norm_key for alias in candidate_aliases):
            return key
    return ''


def _display_aa_table(models: list[dict[str, Any]], aa_data: dict[str, dict[str, float]]) -> None:
    table = Table(title='Codex Model Benchmarks', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Intelligence', justify='right')
    table.add_column('Coding', justify='right')
    table.add_column('Match', justify='right')

    for model in models:
        model_id = str(model['id'])
        aliases = {str(model.get('display_name') or '')}
        match = _find_aa_match(model_id, aa_data, aliases=aliases)
        intelligence = aa_data.get(match, {}).get(_REASONING_INDEX, 0.0)
        coding = aa_data.get(match, {}).get(_CODING_INDEX, 0.0)
        table.add_row(
            model_id,
            f'{intelligence:.1f}' if intelligence else '[dim]no data[/dim]',
            f'{coding:.1f}' if coding else '[dim]no data[/dim]',
            'AA' if match else '[dim]none[/dim]',
        )

    console.print()
    console.print(table)
    console.print('[dim]Artificial Analysis metrics are informational only; choose each tier manually.[/dim]')


def _interactive_select_models(models: list[dict[str, Any]]) -> dict[str, str] | None:
    mapping: dict[str, str] = {}
    options = [str(model['id']) for model in models]

    for tier in ('reasoning', 'orchestration', 'coding', 'review'):
        console.print(f'\n[bold]{tier.title()} model:[/bold]')
        for i, model_id in enumerate(options, 1):
            console.print(f'  [bold][{i}][/bold] {model_id}')

        while True:
            raw = console.input(f'  Select [1-{len(options)}]: ').strip()
            if raw.isdigit():
                index = int(raw)
                if 1 <= index <= len(options):
                    mapping[tier] = options[index - 1]
                    break
            console.print(f'  [red]Enter a number 1-{len(options)}.[/red]')

    response = console.input('\nAccept this mapping? [Y/n] ').strip().lower()
    if response in ('n', 'no'):
        return None
    return mapping


def _config_path() -> str:
    return str(GLOBAL_MODELS_PATH)


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync Codex model tier mapping using benchmarks')
    add_arguments(parser)
    raise SystemExit(run(parser.parse_args()))
