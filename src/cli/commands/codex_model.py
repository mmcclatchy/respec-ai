import json
import os
import re
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

from rich.table import Table

from src.cli.config.global_config import GLOBAL_MODELS_PATH, load_api_key, save_api_key, save_global_models
from src.cli.ui.console import console, print_info, print_warning


_AA_MODELS_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'
_CACHE_DIR = Path.home() / '.config' / 'respec-ai' / 'cache'
_CACHE_TTL_SECONDS = 12 * 60 * 60
_REASONING_INDEX = 'artificial_analysis_intelligence_index'
_CODING_INDEX = 'artificial_analysis_coding_index'

_CODEX_CATALOG: list[dict[str, Any]] = [
    {'id': 'gpt-5.4', 'reasoning_prior': 1.0, 'speed_prior': 0.35, 'cost_prior': 0.2, 'aliases': ['gpt 5.4']},
    {
        'id': 'gpt-5.4-mini',
        'reasoning_prior': 0.65,
        'speed_prior': 0.9,
        'cost_prior': 0.9,
        'aliases': ['gpt 5.4 mini'],
    },
    {
        'id': 'gpt-5.3-codex',
        'reasoning_prior': 0.75,
        'speed_prior': 0.6,
        'cost_prior': 0.55,
        'aliases': ['gpt 5.3 codex'],
    },
    {
        'id': 'gpt-5.2-codex',
        'reasoning_prior': 0.7,
        'speed_prior': 0.72,
        'cost_prior': 0.65,
        'aliases': ['gpt 5.2 codex'],
    },
    {'id': 'gpt-5.2', 'reasoning_prior': 0.8, 'speed_prior': 0.55, 'cost_prior': 0.4, 'aliases': ['gpt 5.2']},
    {
        'id': 'gpt-5.1-codex-max',
        'reasoning_prior': 0.82,
        'speed_prior': 0.45,
        'cost_prior': 0.3,
        'aliases': ['gpt 5.1 codex max'],
    },
    {
        'id': 'gpt-5.1-codex-mini',
        'reasoning_prior': 0.58,
        'speed_prior': 0.88,
        'cost_prior': 0.88,
        'aliases': ['gpt 5.1 codex mini'],
    },
    {'id': 'gpt-5', 'reasoning_prior': 0.72, 'speed_prior': 0.65, 'cost_prior': 0.5, 'aliases': ['gpt 5']},
]


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument('--yes', '-y', action='store_true', help='Accept recommended mapping without prompting')
    parser.add_argument(
        '--aa-key',
        help='Artificial Analysis API key (overrides ARTIFICIAL_ANALYSIS_API_KEY env var)',
    )
    parser.add_argument('--debug', action='store_true', help='Print debug info for API calls')
    parser.add_argument('--no-cache', action='store_true', help='Bypass cached API responses')
    parser.add_argument('--reasoning-model', help='Set reasoning model directly')
    parser.add_argument('--task-model', help='Set task model directly')


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
        save_global_models(mapping, provider='codex')
        console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
        print_info("Run 'respec-ai regenerate' to apply new models to your config")
        return 0

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

    models = [entry['id'] for entry in _CODEX_CATALOG]
    console.print('Provider: [cyan]codex[/cyan]')
    console.print(f'Available models: {", ".join(models)}\n')

    if aa_key:
        print_info('Fetching benchmark data from Artificial Analysis...')
        aa_data = _fetch_aa_data(aa_key, debug=debug)
    else:
        print_warning('ARTIFICIAL_ANALYSIS_API_KEY not set — using catalog defaults for recommendations')
        aa_data = {}

    scored = _score_models(models, aa_data)
    _display_model_table(scored)

    suggestion = _suggest_tiers(scored)
    mapping = suggestion if getattr(args, 'yes', False) else _interactive_override(scored)
    if mapping is None:
        print_warning('Mapping not saved')
        return 1

    save_global_models(mapping, provider='codex')
    console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
    print_info("Run 'respec-ai regenerate' to apply new models to your config")
    return 0


def _warn_if_unknown_mapping(mapping: dict[str, str]) -> None:
    known = {entry['id'] for entry in _CODEX_CATALOG}
    for tier, model in mapping.items():
        if model not in known:
            print_warning(f'{tier.title()} model "{model}" is not in the built-in Codex catalog; saving anyway')


def _read_cache(name: str) -> dict | None:
    path = _CACHE_DIR / f'{name}.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if time.time() - data.get('_cached_at', 0) > _CACHE_TTL_SECONDS:
            return None
        return data.get('payload')
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


def _fetch_aa_data(aa_key: str, *, debug: bool = False) -> dict[str, dict[str, float]]:
    cached = _read_cache('aa_data_codex')
    if cached is not None:
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
        print_warning('Could not fetch Artificial Analysis data — using catalog defaults')
        return {}


def _normalize_name(name: str) -> str:
    lowered = name.lower().replace('-', ' ').replace('_', ' ')
    return re.sub(r'\s+', ' ', lowered).strip()


def _find_aa_match(model_id: str, aa_data: dict[str, dict[str, float]]) -> str:
    model_norm = _normalize_name(model_id)
    aliases = {model_norm}
    for entry in _CODEX_CATALOG:
        if entry['id'] == model_id:
            aliases.update(_normalize_name(alias) for alias in entry.get('aliases', []))
            break
    for key in aa_data:
        norm_key = _normalize_name(key)
        if norm_key in aliases:
            return key
    for key in aa_data:
        norm_key = _normalize_name(key)
        if any(alias in norm_key for alias in aliases):
            return key
    return ''


def _score_models(models: list[str], aa_data: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    catalog = {entry['id']: entry for entry in _CODEX_CATALOG}
    scored: list[dict[str, Any]] = []
    for model_id in models:
        entry = catalog[model_id]
        match = _find_aa_match(model_id, aa_data)
        intelligence = aa_data.get(match, {}).get(_REASONING_INDEX, 0.0)
        coding = aa_data.get(match, {}).get(_CODING_INDEX, 0.0)

        # Prefer AA metrics when available, but preserve deterministic catalog fallback.
        reasoning_score = intelligence if intelligence > 0 else float(entry['reasoning_prior']) * 100
        task_score = coding if coding > 0 else float((entry['speed_prior'] * 0.6 + entry['cost_prior'] * 0.4) * 100)

        if intelligence >= 85:
            insight = 'Strong for complex planning; may trade off speed/cost.'
        elif coding >= 80:
            insight = 'Strong coding throughput; good task-agent default.'
        elif entry['speed_prior'] >= 0.8:
            insight = 'Fast/cost-efficient profile; suited for high-volume tasks.'
        else:
            insight = 'Balanced profile; solid general-purpose fallback.'

        scored.append(
            {
                'model_id': model_id,
                'intelligence': intelligence,
                'coding': coding,
                'reasoning_score': reasoning_score,
                'task_score': task_score,
                'insight': insight,
            }
        )
    return scored


def _display_model_table(scored: list[dict[str, Any]]) -> None:
    table = Table(title='Codex Model Benchmarks', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Intelligence', justify='right')
    table.add_column('Coding', justify='right')
    table.add_column('Recommended Tier')
    table.add_column('Insight')

    reasoning_top = max(scored, key=lambda r: r['reasoning_score'])['model_id']
    task_top = max(scored, key=lambda r: r['task_score'])['model_id']
    for row in scored:
        model_id = row['model_id']
        tiers: list[str] = []
        if model_id == reasoning_top:
            tiers.append('Reasoning')
        if model_id == task_top:
            tiers.append('Task')
        tier_text = ', '.join(tiers) if tiers else '-'
        intelligence = row['intelligence']
        coding = row['coding']
        table.add_row(
            model_id,
            f'{intelligence:.1f}' if intelligence else '[dim]no data[/dim]',
            f'{coding:.1f}' if coding else '[dim]no data[/dim]',
            tier_text,
            row['insight'],
        )
    console.print()
    console.print(table)


def _suggest_tiers(scored: list[dict[str, Any]]) -> dict[str, str]:
    reasoning = max(scored, key=lambda r: r['reasoning_score'])['model_id']
    task = max(scored, key=lambda r: r['task_score'])['model_id']
    return {'reasoning': reasoning, 'task': task}


def _interactive_override(scored: list[dict[str, Any]]) -> dict[str, str] | None:
    reasoning_sorted = sorted(scored, key=lambda r: r['reasoning_score'], reverse=True)
    task_sorted = sorted(scored, key=lambda r: r['task_score'], reverse=True)
    mapping: dict[str, str] = {}

    for tier, options, score_key in (
        ('reasoning', reasoning_sorted, 'reasoning_score'),
        ('task', task_sorted, 'task_score'),
    ):
        console.print(f'\n[bold]{tier.title()} model:[/bold]')
        for i, row in enumerate(options, 1):
            console.print(f'  [bold][{i}][/bold] {row["model_id"]}  ({row[score_key]:.1f})')

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


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync Codex model tier mapping using benchmarks')
    add_arguments(parser)
    raise SystemExit(run(parser.parse_args()))
