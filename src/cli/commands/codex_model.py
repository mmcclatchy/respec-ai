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


_AA_MODELS_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'
_CACHE_DIR = Path.home() / '.config' / 'respec-ai' / 'cache'
_CACHE_TTL_SECONDS = 12 * 60 * 60
_REASONING_INDEX = 'artificial_analysis_intelligence_index'
_CODING_INDEX = 'artificial_analysis_coding_index'
_CODEX_APP_SERVER_CMD = ['codex', 'app-server', '--listen', 'stdio://']
_CODEX_DISCOVERY_CACHE_KEY = 'codex_models_discovered'
_CODEX_DISCOVERY_TIMEOUT_SECONDS = 15
_CODEX_DISCOVERY_PAGE_LIMIT = 100

_KNOWN_PRIORS: dict[str, dict[str, Any]] = {
    'gpt-5.4': {'reasoning_prior': 1.0, 'speed_prior': 0.35, 'cost_prior': 0.2, 'aliases': ['gpt 5.4']},
    'gpt-5.4-mini': {
        'reasoning_prior': 0.65,
        'speed_prior': 0.9,
        'cost_prior': 0.9,
        'aliases': ['gpt 5.4 mini'],
    },
    'gpt-5.3-codex': {
        'reasoning_prior': 0.75,
        'speed_prior': 0.6,
        'cost_prior': 0.55,
        'aliases': ['gpt 5.3 codex'],
    },
    'gpt-5.3-codex-spark': {
        'reasoning_prior': 0.6,
        'speed_prior': 0.98,
        'cost_prior': 0.95,
        'aliases': ['gpt 5.3 codex spark'],
    },
    'gpt-5.2-codex': {
        'reasoning_prior': 0.7,
        'speed_prior': 0.72,
        'cost_prior': 0.65,
        'aliases': ['gpt 5.2 codex'],
    },
    'gpt-5.2': {'reasoning_prior': 0.8, 'speed_prior': 0.55, 'cost_prior': 0.4, 'aliases': ['gpt 5.2']},
    'gpt-5.1-codex-max': {
        'reasoning_prior': 0.82,
        'speed_prior': 0.45,
        'cost_prior': 0.3,
        'aliases': ['gpt 5.1 codex max'],
    },
    'gpt-5.1-codex-mini': {
        'reasoning_prior': 0.58,
        'speed_prior': 0.88,
        'cost_prior': 0.88,
        'aliases': ['gpt 5.1 codex mini'],
    },
    'gpt-5': {'reasoning_prior': 0.72, 'speed_prior': 0.65, 'cost_prior': 0.5, 'aliases': ['gpt 5']},
}


_MODEL_VERSION_RE = re.compile(r'^gpt-(\d+)(?:\.(\d+))?(?:\.(\d+))?')


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument('--yes', '-y', action='store_true', help='Accept recommended mapping without prompting')
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
    parser.add_argument('--reasoning-model', help='Set reasoning model directly')
    parser.add_argument('--task-model', help='Set task model directly')
    parser.add_argument(
        '--no-apply',
        action='store_true',
        help='Save global model mapping only (skip forced regenerate for current codex project)',
    )


def run(args: Namespace) -> int:
    direct_reasoning = getattr(args, 'reasoning_model', None)
    direct_task = getattr(args, 'task_model', None)
    if direct_reasoning or direct_task:
        reasoning = str((direct_reasoning or direct_task or '')).strip()
        task = str((direct_task or direct_reasoning or '')).strip()
        if not reasoning or not task:
            print_warning('Could not derive both reasoning and task models from provided arguments')
            return 1
        mapping: dict[str, str] = {'reasoning': reasoning, 'task': task}
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

    discovered = _discover_codex_models(include_hidden=include_hidden, debug=debug)
    if not discovered:
        return 1

    models = [entry['id'] for entry in discovered]
    model_metadata = {entry['id']: entry for entry in discovered}

    console.print('Provider: [cyan]codex[/cyan]')
    console.print(f'Available models: {", ".join(models)}\n')

    if aa_key:
        print_info('Fetching benchmark data from Artificial Analysis...')
        aa_data = _fetch_aa_data(aa_key, debug=debug)
    else:
        print_warning('ARTIFICIAL_ANALYSIS_API_KEY not set — using local priors for recommendations')
        aa_data = {}

    scored = _score_models(models, aa_data, model_metadata=model_metadata)
    suggestion = _suggest_tiers(scored)
    _display_model_table(scored, suggestion)
    mapping = suggestion if getattr(args, 'yes', False) else _interactive_override(scored)
    if mapping is None:
        print_warning('Mapping not saved')
        return 1

    _warn_if_unknown_mapping(mapping, known_models=set(models))
    return _save_and_apply(mapping, no_apply=bool(getattr(args, 'no_apply', False)))


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
    from src.cli.commands import regenerate

    return regenerate.run(Namespace(force=True))


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
        print_warning('Could not fetch Artificial Analysis data — using local priors')
        return {}


def _normalize_name(name: str) -> str:
    lowered = name.lower().replace('-', ' ').replace('_', ' ')
    return re.sub(r'\s+', ' ', lowered).strip()


def _prior_profile(model_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    known = _KNOWN_PRIORS.get(model_id)
    if known is not None:
        return dict(known)

    description = str(metadata.get('description') or '').lower()
    display_name = str(metadata.get('display_name') or '').lower()
    text = f'{model_id.lower()} {display_name} {description}'

    profile = {
        'reasoning_prior': 0.72,
        'speed_prior': 0.65,
        'cost_prior': 0.5,
        'aliases': [_normalize_name(model_id)],
    }

    if 'spark' in text:
        profile.update({'reasoning_prior': 0.6, 'speed_prior': 0.98, 'cost_prior': 0.95})
    elif 'mini' in text:
        profile.update({'reasoning_prior': 0.62, 'speed_prior': 0.9, 'cost_prior': 0.88})
    elif 'max' in text:
        profile.update({'reasoning_prior': 0.84, 'speed_prior': 0.45, 'cost_prior': 0.3})
    elif 'codex' in text:
        profile.update({'reasoning_prior': 0.78, 'speed_prior': 0.63, 'cost_prior': 0.55})

    if bool(metadata.get('is_default')):
        profile['reasoning_prior'] = max(profile['reasoning_prior'], 0.95)

    return profile


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


def _score_models(
    models: list[str],
    aa_data: dict[str, dict[str, float]],
    *,
    model_metadata: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    metadata_map = model_metadata or {}
    scored: list[dict[str, Any]] = []

    for model_id in models:
        metadata = metadata_map.get(model_id, {})
        profile = _prior_profile(model_id, metadata)
        aliases = set(profile.get('aliases', []))
        display_name = str(metadata.get('display_name') or '')
        if display_name:
            aliases.add(display_name)

        match = _find_aa_match(model_id, aa_data, aliases=aliases)
        intelligence = aa_data.get(match, {}).get(_REASONING_INDEX, 0.0)
        coding = aa_data.get(match, {}).get(_CODING_INDEX, 0.0)

        reasoning_prior = float(profile['reasoning_prior'])
        speed_prior = float(profile['speed_prior'])
        cost_prior = float(profile['cost_prior'])

        # Prefer AA metrics when available, but preserve deterministic local fallback.
        capability_score = intelligence if intelligence > 0 else reasoning_prior * 100
        speed_score = coding if coding > 0 else speed_prior * 100
        reasoning_score = capability_score
        task_score = coding if coding > 0 else (speed_prior * 0.6 + cost_prior * 0.4) * 100

        if intelligence >= 85:
            insight = 'Strong for complex planning; may trade off speed/cost.'
        elif coding >= 80:
            insight = 'Strong coding throughput; good task-agent default.'
        elif speed_prior >= 0.8:
            insight = 'Fast/cost-efficient profile; suited for high-volume tasks.'
        else:
            insight = 'Balanced profile; solid general-purpose fallback.'

        scored.append(
            {
                'model_id': model_id,
                'intelligence': intelligence,
                'coding': coding,
                'capability_score': capability_score,
                'speed_score': speed_score,
                'cost_affordability': cost_prior * 100,
                'has_aa_capability': intelligence > 0,
                'has_aa_speed': coding > 0,
                'reasoning_score': reasoning_score,
                'task_score': task_score,
                'insight': insight,
            }
        )

    return scored


def _display_model_table(scored: list[dict[str, Any]], suggestion: dict[str, str]) -> None:
    table = Table(title='Codex Model Comparison', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Capability', justify='right')
    table.add_column('Speed', justify='right')
    table.add_column('Coding', justify='right')
    table.add_column('Cost', justify='right')
    table.add_column('Data', justify='right')
    table.add_column('Recommended Tier')
    table.add_column('Insight')

    reasoning_top = suggestion.get('reasoning', '')
    task_top = suggestion.get('task', '')
    for row in scored:
        model_id = row['model_id']
        tiers: list[str] = []
        if model_id == reasoning_top:
            tiers.append('Reasoning')
        if model_id == task_top:
            tiers.append('Task')
        tier_text = ', '.join(tiers) if tiers else '-'
        capability_score = float(row['capability_score'])
        speed_score = float(row['speed_score'])
        cost_affordability = float(row['cost_affordability'])
        intelligence = float(row['intelligence'])
        coding = float(row['coding'])
        data_source = _format_data_source(
            has_aa_capability=bool(row['has_aa_capability']),
            has_aa_speed=bool(row['has_aa_speed']),
        )
        capability = _format_metric(
            score=capability_score,
            aa_score=intelligence,
            has_aa=bool(row['has_aa_capability']),
        )
        speed = _format_metric(
            score=speed_score,
            aa_score=coding,
            has_aa=bool(row['has_aa_speed']),
        )
        coding_text = f'{coding:.1f}' if bool(row['has_aa_speed']) else '[dim]n/a[/dim]'
        table.add_row(
            model_id,
            capability,
            speed,
            coding_text,
            _cost_symbol(cost_affordability),
            data_source,
            tier_text,
            row['insight'],
        )
    console.print()
    console.print(table)
    console.print('[dim]Legend: Data=AA (benchmark-backed), Inferred (local priors).[/dim]')
    console.print('[dim]Coding is the raw AA coding benchmark when available.[/dim]')
    console.print('[dim]Auto-recommendations prioritize AA-backed models when available.[/dim]')


def _suggest_tiers(scored: list[dict[str, Any]]) -> dict[str, str]:
    if not scored:
        return {}

    reasoning_candidates = [row for row in scored if row['has_aa_capability']]
    if reasoning_candidates:
        reasoning = max(reasoning_candidates, key=lambda r: r['reasoning_score'])['model_id']
    else:
        fallback_reasoning = _pick_reasoning_fallback([str(row['model_id']) for row in scored])
        reasoning = fallback_reasoning or max(scored, key=lambda r: r['reasoning_score'])['model_id']

    codex_scored = [row for row in scored if _is_codex_model(str(row['model_id']))]
    task_candidates = [row for row in codex_scored if row['has_aa_speed']]
    if task_candidates:
        task = max(task_candidates, key=lambda r: r['task_score'])['model_id']
    else:
        fallback_task = _pick_task_codex_fallback([str(row['model_id']) for row in codex_scored])
        if fallback_task:
            task = fallback_task
        elif codex_scored:
            task = max(codex_scored, key=lambda r: r['task_score'])['model_id']
        else:
            task = max(scored, key=lambda r: r['task_score'])['model_id']

    return {'reasoning': reasoning, 'task': task}


def _interactive_override(scored: list[dict[str, Any]]) -> dict[str, str] | None:
    reasoning_sorted = sorted(
        scored,
        key=lambda r: (bool(r['has_aa_capability']), float(r['reasoning_score'])),
        reverse=True,
    )
    task_sorted = sorted(
        scored,
        key=lambda r: (bool(r['has_aa_speed']), float(r['task_score'])),
        reverse=True,
    )
    mapping: dict[str, str] = {}

    for tier, options, score_key in (
        ('reasoning', reasoning_sorted, 'reasoning_score'),
        ('task', task_sorted, 'task_score'),
    ):
        console.print(f'\n[bold]{tier.title()} model:[/bold]')
        for i, row in enumerate(options, 1):
            source = _format_data_source(
                has_aa_capability=bool(row['has_aa_capability']),
                has_aa_speed=bool(row['has_aa_speed']),
            )
            console.print(f'  [bold][{i}][/bold] {row["model_id"]}  ({row[score_key]:.1f}, {source})')

        while True:
            raw = console.input(f'  Select [1-{len(options)}]: ').strip()
            if raw.isdigit():
                index = int(raw)
                if 1 <= index <= len(options):
                    mapping[tier] = options[index - 1]['model_id']
                    break
            console.print(f'  [red]Enter a number 1-{len(options)}.[/red]')

    response = console.input('\nAccept this mapping? [Y/n] ').strip().lower()
    if response in ('n', 'no'):
        return None
    return mapping


def _config_path() -> str:
    return str(GLOBAL_MODELS_PATH)


def _format_metric(*, score: float, aa_score: float, has_aa: bool) -> str:
    if has_aa:
        band = _metric_band(score)
        return f'{band} ({aa_score:.1f})'
    conservative_score = _conservative_inferred_score(score)
    band = _metric_band(conservative_score)
    return f'{band} [dim](inferred, conservative)[/dim]'


def _metric_band(score: float) -> str:
    if score >= 75:
        return 'Very High'
    if score >= 60:
        return 'High'
    if score >= 45:
        return 'Medium'
    if score >= 30:
        return 'Low'
    return 'Very Low'


def _conservative_inferred_score(score: float) -> float:
    # Inferred priors are useful for relative ordering, but we present them conservatively
    # to avoid implying benchmark-level certainty.
    return 35.0 + (max(0.0, min(score, 100.0)) * 0.35)


def _cost_symbol(cost_affordability: float) -> str:
    if cost_affordability >= 90:
        return '$'
    if cost_affordability >= 75:
        return '$$'
    if cost_affordability >= 60:
        return '$$$'
    if cost_affordability >= 45:
        return '$$$$'
    return '$$$$$'


def _format_data_source(*, has_aa_capability: bool, has_aa_speed: bool) -> str:
    if has_aa_capability and has_aa_speed:
        return 'AA'
    if has_aa_capability or has_aa_speed:
        return 'AA partial'
    return 'Inferred'


def _extract_model_version(model_id: str) -> tuple[int, int, int] | None:
    match = _MODEL_VERSION_RE.match(model_id)
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    return (major, minor, patch)


def _pick_reasoning_fallback(models: list[str]) -> str:
    candidates: list[str] = []
    for model_id in models:
        if _extract_model_version(model_id) is None:
            continue
        lowered = model_id.lower()
        if '-mini' in lowered or '-spark' in lowered:
            continue
        candidates.append(model_id)

    if not candidates:
        return ''
    return max(candidates, key=_fallback_sort_key)


def _pick_task_codex_fallback(models: list[str]) -> str:
    base_codex = [model_id for model_id in models if model_id.lower().endswith('-codex')]
    if base_codex:
        return max(base_codex, key=_fallback_sort_key)

    codex_variants = [model_id for model_id in models if '-codex' in model_id.lower()]
    if codex_variants:
        return max(codex_variants, key=_fallback_sort_key)
    return ''


def _is_codex_model(model_id: str) -> bool:
    return '-codex' in model_id.lower()


def _fallback_sort_key(model_id: str) -> tuple[tuple[int, int, int], int, int]:
    version = _extract_model_version(model_id) or (-1, -1, -1)
    lowered = model_id.lower()
    variant_rank = 0
    if '-mini' in lowered:
        variant_rank = -3
    elif '-spark' in lowered:
        variant_rank = -2
    elif '-max' in lowered:
        variant_rank = -1
    return (version, variant_rank, -len(model_id))


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync Codex model tier mapping using benchmarks')
    add_arguments(parser)
    raise SystemExit(run(parser.parse_args()))
