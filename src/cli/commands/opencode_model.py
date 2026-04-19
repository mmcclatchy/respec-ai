import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

from exa_py import Exa
from rich.table import Table

from src.cli.config.global_config import GLOBAL_MODELS_PATH, load_api_key, save_api_key, save_global_models
from src.cli.ui.console import console, print_error, print_info, print_warning


_AA_MODELS_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'
_OPENCODE_GO_DOCS_URL = 'https://opencode.ai/docs/go/'
_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
_CACHE_DIR = Path.home() / '.config' / 'respec-ai' / 'cache'
_CACHE_TTL_SECONDS = 12 * 60 * 60


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


_REASONING_INDEX = 'artificial_analysis_intelligence_index'
_CODING_INDEX = 'artificial_analysis_coding_index'


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        help='Accept recommended mapping without prompting',
    )
    parser.add_argument(
        '--aa-key',
        help='Artificial Analysis API key (overrides ARTIFICIAL_ANALYSIS_API_KEY env var)',
    )
    parser.add_argument(
        '--exa-key',
        help='Exa API key for rate limit lookup (overrides EXA_API_KEY env var)',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print debug info for API calls',
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Bypass cached API responses',
    )
    parser.add_argument('--reasoning-model', help='Set reasoning model directly')
    parser.add_argument('--orchestration-model', help='Set orchestration model directly')
    parser.add_argument('--task-model', dest='orchestration_model', help='Alias for --orchestration-model')
    parser.add_argument('--coding-model', help='Set coding model directly')
    parser.add_argument('--review-model', help='Set review model directly')


def run(args: Namespace) -> int:
    direct_reasoning = getattr(args, 'reasoning_model', None)
    direct_orchestration = getattr(args, 'orchestration_model', None) or getattr(args, 'task_model', None)
    direct_coding = getattr(args, 'coding_model', None)
    direct_review = getattr(args, 'review_model', None)
    if direct_reasoning or direct_orchestration or direct_coding or direct_review:
        mapping = _build_direct_mapping(direct_reasoning, direct_orchestration, direct_coding, direct_review)
        if mapping is None:
            return 1
        save_global_models(mapping, provider='opencode')
        console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
        print_info("Run 'respec-ai regenerate' to apply new models to your config")
        return 0

    aa_key = (
        getattr(args, 'aa_key', None)
        or os.environ.get('ARTIFICIAL_ANALYSIS_API_KEY', '')
        or load_api_key('artificial_analysis')
        or ''
    )
    exa_key = getattr(args, 'exa_key', None) or os.environ.get('EXA_API_KEY', '') or load_api_key('exa') or ''
    if aa_key and getattr(args, 'aa_key', None):
        save_api_key('artificial_analysis', aa_key)
    if exa_key and getattr(args, 'exa_key', None):
        save_api_key('exa', exa_key)
    if getattr(args, 'no_cache', False):
        _clear_cache()
    debug = getattr(args, 'debug', False)

    provider, models = _discover_models()
    if not models:
        print_error('No OpenCode models found. Ensure opencode is installed and configured.')
        return 1

    console.print(f'Provider: [cyan]{provider}[/cyan]')
    console.print(f'Available models: {", ".join(models)}\n')

    if aa_key:
        print_info('Fetching benchmark data from Artificial Analysis...')
        aa_data = _fetch_aa_data(aa_key, debug=debug)
    else:
        print_warning('ARTIFICIAL_ANALYSIS_API_KEY not set — skipping benchmark lookup')
        print_warning('Set ARTIFICIAL_ANALYSIS_API_KEY or use --aa-key for benchmark-backed recommendations')
        aa_data = {}

    rate_limits: dict[str, str] = {}
    if exa_key:
        rate_limits = _fetch_rate_limits(exa_key, provider, debug=debug)

    scored_by_tier = _score_models_by_tier(models, aa_data, rate_limits=rate_limits, debug=debug)
    suggestion = _suggest_tiers(scored_by_tier)
    _display_model_comparison(
        scored_by_tier.get('metrics', {}),
        suggestion=suggestion,
        rate_limits=rate_limits,
    )

    if getattr(args, 'yes', False):
        mapping = suggestion
    else:
        mapping = _interactive_override(suggestion, scored_by_tier)
        if mapping is None:
            print_warning('Mapping not saved')
            return 1

    if 'task' not in mapping:
        fallback = mapping.get('orchestration') or mapping.get('reasoning')
        if fallback:
            mapping = {**mapping, 'task': fallback}

    save_global_models(mapping, provider='opencode')
    console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
    print_info("Run 'respec-ai regenerate' to apply new models to your config")
    return 0


def _build_direct_mapping(
    reasoning: str | None,
    orchestration: str | None,
    coding: str | None,
    review: str | None,
) -> dict[str, str] | None:
    reasoning_value = str(reasoning or orchestration or coding or review or '').strip()
    orchestration_value = str(orchestration or coding or review or reasoning_value).strip()
    coding_value = str(coding or orchestration_value or reasoning_value or review or '').strip()
    review_value = str(review or reasoning_value or coding_value or orchestration_value or '').strip()
    if not reasoning_value or not orchestration_value or not coding_value or not review_value:
        print_warning('Could not derive all four model categories from provided arguments')
        return None
    return {
        'reasoning': reasoning_value,
        'orchestration': orchestration_value,
        'coding': coding_value,
        'review': review_value,
    }


def _discover_models() -> tuple[str, list[str]]:
    provider = _detect_provider()
    if not provider:
        return '', []
    models = _list_models(provider)
    return provider, models


def _detect_provider() -> str:
    try:
        result = subprocess.run(
            ['opencode', 'providers', 'list'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        clean = _ANSI_ESCAPE.sub('', result.stdout)
        for line in clean.splitlines():
            if '●' not in line:
                continue
            name_part = line.split('●', 1)[1].strip()
            name_part = re.split(r'\s+api\b', name_part, flags=re.IGNORECASE)[0].strip()
            if name_part:
                return name_part.lower().replace(' ', '-')
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ''


def _list_models(provider: str) -> list[str]:
    try:
        result = subprocess.run(
            ['opencode', 'models', provider],
            capture_output=True,
            text=True,
            timeout=10,
        )
        models = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped and '/' in stripped:
                models.append(stripped)
        return models
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _fetch_aa_data(aa_key: str, *, debug: bool = False) -> dict[str, dict[str, float]]:
    cached = _read_cache('aa_data')
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
        if debug:
            console.print(f'[dim]  AA response type: {type(data).__name__}, models: {len(models_list)}[/dim]')
        with_evals = 0
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
                with_evals += 1
        if debug:
            console.print(f'[dim]  AA models with scores: {with_evals}/{len(models_list)}[/dim]')
        _write_cache('aa_data', result)
        return result
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        if debug:
            console.print(f'[red]  AA error: {type(exc).__name__}: {exc}[/red]')
        print_warning('Could not fetch Artificial Analysis data — falling back to interactive selection')
        return {}


def _fetch_rate_limits(exa_key: str, provider: str, *, debug: bool = False) -> dict[str, str]:
    cached = _read_cache('rate_limits')
    if cached is not None:
        if debug:
            console.print(f'[dim]  Exa using cached rate limits ({len(cached)} models)[/dim]')
        return cached
    if debug:
        console.print(f'[dim]  Exa get_contents({_OPENCODE_GO_DOCS_URL})[/dim]')
    try:
        exa = Exa(api_key=exa_key)
        response = exa.get_contents(urls=[_OPENCODE_GO_DOCS_URL], text=True)
        if not response.results:
            if debug:
                console.print('[dim]  Exa returned no results[/dim]')
            return {}
        text = response.results[0].text or ''
        if debug:
            console.print(f'[dim]  Exa text length: {len(text)} chars[/dim]')
            console.print(f'[dim]  Exa text preview: {text[:300]!r}[/dim]')
        parsed = _parse_rate_limits_table(text, provider)
        if debug:
            console.print(f'[dim]  Parsed rate limits: {parsed}[/dim]')
        if parsed:
            _write_cache('rate_limits', parsed)
        return parsed
    except Exception as exc:
        if debug:
            console.print(f'[red]  Exa error: {type(exc).__name__}: {exc}[/red]')
        print_warning('Could not fetch rate limits — skipping')
        return {}


def _parse_rate_limits_table(text: str, provider: str) -> dict[str, str]:
    lines = text.splitlines()
    header_line = ''
    data_line = ''
    for i, line in enumerate(lines):
        if 'requests per 5 hour' in line.lower():
            data_line = line
            for j in range(i - 1, -1, -1):
                candidate = lines[j].strip()
                if candidate.startswith('|') and '---' not in candidate:
                    header_line = candidate
                    break
            break

    if not header_line or not data_line:
        return {}

    headers = [h.strip() for h in header_line.split('|') if h.strip()]
    values = [v.strip() for v in data_line.split('|') if v.strip()]

    if values and values[0].lower().startswith('requests'):
        values = values[1:]

    result: dict[str, str] = {}
    for name, val in zip(headers, values):
        model_id = f'{provider}/{name.lower().replace(" ", "-")}'
        result[model_id] = val
    return result


def _parse_rate_limit_value(val: str) -> int:
    return int(val.replace(',', '').strip())


def _score_models_by_tier(
    models: list[str],
    aa_data: dict[str, dict[str, float]],
    rate_limits: dict[str, str] | None = None,
    *,
    debug: bool = False,
) -> dict[str, Any]:
    reasoning_scored: list[tuple[str, float]] = []
    orchestration_scored: list[tuple[str, float]] = []
    task_scored: list[tuple[str, float]] = []
    coding_scored: list[tuple[str, float]] = []
    review_scored: list[tuple[str, float]] = []
    metrics: dict[str, dict[str, float]] = {}

    parsed_rates: dict[str, int] = {}
    if rate_limits:
        parsed_rates = {m: _parse_rate_limit_value(v) for m, v in rate_limits.items()}

    for model_id in models:
        short = model_id.split('/', 1)[-1].lower()
        match = _find_aa_match(short, aa_data)
        if debug:
            status = f'matched "{match}"' if match else 'no match'
            console.print(f'[dim]  {model_id} -> {status}[/dim]')

        intelligence = aa_data[match].get(_REASONING_INDEX, 0.0) if match else 0.0
        coding = aa_data[match].get(_CODING_INDEX, 0.0) if match else 0.0
        reasoning_scored.append((model_id, intelligence))

        throughput = float(parsed_rates.get(model_id, 0))
        task_scored.append((model_id, throughput))
        orchestration_score = throughput if throughput > 0 else max(intelligence, coding)
        coding_score = coding if coding > 0 else orchestration_score
        review_score = (intelligence + coding_score) / 2 if (intelligence > 0 or coding_score > 0) else 0.0
        orchestration_scored.append((model_id, orchestration_score))
        coding_scored.append((model_id, coding_score))
        review_scored.append((model_id, review_score))
        metrics[model_id] = {'intelligence': intelligence, 'coding': coding, 'throughput': throughput}

    return {
        'reasoning': sorted(reasoning_scored, key=lambda x: x[1], reverse=True),
        'orchestration': sorted(orchestration_scored, key=lambda x: x[1], reverse=True),
        'coding': sorted(coding_scored, key=lambda x: x[1], reverse=True),
        'review': sorted(review_scored, key=lambda x: x[1], reverse=True),
        'task': sorted(task_scored, key=lambda x: x[1], reverse=True),
        'metrics': metrics,
    }


def _normalize_name(name: str) -> str:
    return name.lower().replace('-', ' ').replace('_', ' ').strip()


def _find_aa_match(short_name: str, aa_data: dict[str, dict[str, float]]) -> str:
    normalized = _normalize_name(short_name)
    candidates: list[tuple[int, str]] = []
    for key in aa_data:
        norm_key = _normalize_name(key)
        if norm_key == normalized:
            return key
        if norm_key.startswith(normalized + ' ('):
            candidates.append((len(norm_key), key))
    if candidates:
        candidates.sort()
        return candidates[0][1]
    return ''


def _suggest_tiers(scored_by_tier: dict[str, list[tuple[str, float]]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    reasoning = scored_by_tier.get('reasoning', [])
    orchestration = scored_by_tier.get('orchestration', [])
    coding = scored_by_tier.get('coding', [])
    review = scored_by_tier.get('review', [])
    if not orchestration and scored_by_tier.get('task'):
        task = scored_by_tier.get('task', [])
        if reasoning:
            mapping['reasoning'] = reasoning[0][0]
        has_throughput = any(score > 0 for _, score in task)
        if has_throughput:
            mapping['task'] = task[0][0]
        elif len(reasoning) >= 2:
            mapping['task'] = reasoning[1][0]
        elif reasoning:
            mapping['task'] = reasoning[0][0]
        return mapping
    if reasoning:
        mapping['reasoning'] = reasoning[0][0]
    if orchestration:
        mapping['orchestration'] = orchestration[0][0]
    if coding:
        mapping['coding'] = coding[0][0]
    if review:
        mapping['review'] = review[0][0]
    return mapping


def _display_tier_table(
    title: str,
    scored: list[tuple[str, float]],
    score_label: str,
    rate_limits: dict[str, str],
    extra_scores: dict[str, float] | None = None,
    extra_label: str = '',
    format_int: bool = False,
) -> None:
    table = Table(title=title, show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column(score_label, justify='right')
    if extra_scores:
        table.add_column(extra_label, justify='right')
    if rate_limits:
        table.add_column('Reqs/5hr', justify='right')
    for model_id, score in scored:
        short = model_id.split('/', 1)[-1]
        if format_int:
            score_text = f'{int(score):,}' if score else '[dim]no data[/dim]'
        else:
            score_text = f'{score:.1f}' if score else '[dim]no data[/dim]'
        row: list[str] = [short, score_text]
        if extra_scores:
            extra = extra_scores.get(model_id, 0.0)
            row.append(f'{extra:.1f}' if extra else '[dim]no data[/dim]')
        if rate_limits:
            row.append(rate_limits.get(model_id, '\u2014'))
        table.add_row(*row)
    console.print()
    console.print(table)


def _display_model_insights(metrics: dict[str, dict[str, float]], rate_limits: dict[str, str]) -> None:
    if not metrics:
        return
    table = Table(title='OpenCode Model Benchmarks', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Intelligence', justify='right')
    table.add_column('Coding', justify='right')
    if rate_limits:
        table.add_column('Reqs/5hr', justify='right')
    table.add_column('Insight')

    top_reasoning = max(metrics.items(), key=lambda item: item[1].get('intelligence', 0.0))[0]
    top_orchestration = max(metrics.items(), key=lambda item: item[1].get('throughput', 0.0))[0]
    top_coding = max(metrics.items(), key=lambda item: item[1].get('coding', 0.0))[0]
    top_review = max(metrics.items(), key=lambda item: item[1].get('intelligence', 0.0) + item[1].get('coding', 0.0))[0]

    for model_id, row in sorted(
        metrics.items(),
        key=lambda item: (
            item[1].get('intelligence', 0.0),
            item[1].get('coding', 0.0),
            item[1].get('throughput', 0.0),
        ),
        reverse=True,
    ):
        intelligence = row.get('intelligence', 0.0)
        coding = row.get('coding', 0.0)
        throughput = row.get('throughput', 0.0)

        if model_id == top_reasoning and intelligence > 0:
            insight = 'Best for planning and deep architecture reasoning.'
        elif model_id == top_orchestration and throughput > 0:
            insight = 'Best throughput for high-volume orchestration workflows.'
        elif model_id == top_coding and coding > 0:
            insight = 'Coding-leaning profile; practical for implementation loops.'
        elif model_id == top_review and (intelligence > 0 or coding > 0):
            insight = 'Balanced profile; practical for review loops.'
        elif intelligence > 0:
            insight = 'Balanced profile; solid fallback when tiers overlap.'
        else:
            insight = 'No benchmark signal; keep as manual/backup option.'

        out = [
            model_id.split('/', 1)[-1],
            f'{intelligence:.1f}' if intelligence else '[dim]no data[/dim]',
            f'{coding:.1f}' if coding else '[dim]no data[/dim]',
        ]
        if rate_limits:
            out.append(rate_limits.get(model_id, '\u2014'))
        out.append(insight)
        table.add_row(*out)
    console.print()
    console.print(table)


def _display_model_comparison(
    metrics: dict[str, dict[str, float]],
    *,
    suggestion: dict[str, str],
    rate_limits: dict[str, str],
) -> None:
    if not metrics:
        return

    table = Table(title='OpenCode Model Comparison', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Capability', justify='right')
    table.add_column('Speed', justify='right')
    table.add_column('Coding', justify='right')
    table.add_column('Cost', justify='right')
    table.add_column('Data', justify='right')
    table.add_column('Recommended Tier')
    table.add_column('Insight')

    for model_id, row in sorted(
        metrics.items(),
        key=lambda item: (
            item[1].get('intelligence', 0.0),
            item[1].get('coding', 0.0),
            item[1].get('throughput', 0.0),
        ),
        reverse=True,
    ):
        intelligence = float(row.get('intelligence', 0.0))
        coding = float(row.get('coding', 0.0))
        throughput = float(row.get('throughput', 0.0))

        has_aa = intelligence > 0 or coding > 0
        capability_score = intelligence if intelligence > 0 else _infer_capability_score(model_id)
        speed_score = coding if coding > 0 else _infer_speed_score(throughput, model_id)
        cost_score = _infer_cost_score(throughput, model_id)

        tiers: list[str] = []
        if model_id == suggestion.get('reasoning'):
            tiers.append('Reasoning')
        if model_id == suggestion.get('orchestration'):
            tiers.append('Orchestration')
        if model_id == suggestion.get('coding'):
            tiers.append('Coding')
        if model_id == suggestion.get('review'):
            tiers.append('Review')
        tier_text = ', '.join(tiers) if tiers else '-'

        if intelligence >= 55:
            insight = 'Strong planning profile for architecture-heavy prompts.'
        elif throughput > 0:
            insight = 'Throughput-oriented profile for high-volume task loops.'
        elif coding > 0 and coding >= intelligence:
            insight = 'Coding-leaning profile; practical implementation option.'
        elif has_aa:
            insight = 'Balanced profile; solid fallback when tiers overlap.'
        else:
            insight = 'No benchmark signal; keep as manual/backup option.'

        table.add_row(
            model_id.split('/', 1)[-1],
            _format_metric(capability_score, aa_score=intelligence, has_aa=intelligence > 0),
            _format_metric(speed_score, aa_score=coding, has_aa=coding > 0),
            f'{coding:.1f}' if coding else '[dim]n/a[/dim]',
            _cost_symbol(cost_score),
            'AA' if has_aa else 'Inferred',
            tier_text,
            insight,
        )

    console.print()
    console.print(table)
    console.print('[dim]Legend: Data=AA (benchmark-backed), Inferred (local heuristics).[/dim]')


def _infer_capability_score(model_id: str) -> float:
    short = model_id.split('/', 1)[-1].lower()
    if any(tag in short for tag in ('pro', 'plus', '2.7', '5.1')):
        return 52.0
    if any(tag in short for tag in ('mini', 'omni', '2.5')):
        return 44.0
    return 48.0


def _infer_speed_score(throughput: float, model_id: str) -> float:
    if throughput > 0:
        return min(95.0, 35.0 + (throughput / 250.0))
    short = model_id.split('/', 1)[-1].lower()
    if any(tag in short for tag in ('mini', 'omni', '2.5')):
        return 56.0
    if any(tag in short for tag in ('pro', 'plus', '2.7')):
        return 50.0
    return 47.0


def _infer_cost_score(throughput: float, model_id: str) -> float:
    if throughput >= 15000:
        return 92.0
    if throughput >= 9000:
        return 82.0
    if throughput >= 3000:
        return 68.0
    if throughput > 0:
        return 54.0
    short = model_id.split('/', 1)[-1].lower()
    if any(tag in short for tag in ('mini', 'omni', '2.5')):
        return 80.0
    if any(tag in short for tag in ('pro', 'plus', '2.7')):
        return 56.0
    return 50.0


def _format_metric(score: float, *, aa_score: float, has_aa: bool) -> str:
    band = _metric_band(score)
    if has_aa:
        return f'{band} ({aa_score:.1f})'
    return f'{band} [dim](inferred)[/dim]'


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


def _interactive_override(
    suggestion: dict[str, str],
    scored_by_tier: dict[str, list[tuple[str, float]]],
) -> dict[str, str] | None:
    mapping: dict[str, str] = {}

    if not scored_by_tier.get('orchestration') and scored_by_tier.get('task'):
        for tier in ('reasoning', 'task'):
            options = scored_by_tier.get(tier, [])
            metrics_raw = scored_by_tier.get('metrics', {})
            metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

            console.print(f'\n[bold]{tier.title()} model:[/bold]')
            for i, (model_id, score) in enumerate(options, 1):
                row = metrics.get(model_id, {})
                has_aa = row.get('intelligence', 0.0) > 0 or row.get('coding', 0.0) > 0
                score_text = f'({score:.1f})' if score else ''
                source = 'AA' if has_aa else 'Inferred'
                console.print(f'  [bold][{i}][/bold] {model_id}  {score_text} [{source}]')

            while True:
                raw = console.input(f'  Select [1-{len(options)}]: ').strip()
                if raw.isdigit():
                    index = int(raw)
                    if 1 <= index <= len(options):
                        mapping[tier] = options[index - 1][0]
                        break
                console.print(f'  [red]Enter a number 1-{len(options)}.[/red]')

        response = console.input('\nAccept this mapping? [Y/n] ').strip().lower()
        if response in ('n', 'no'):
            return None
        return mapping

    for tier in ('reasoning', 'orchestration', 'coding', 'review'):
        options = scored_by_tier.get(tier, [])
        metrics_raw = scored_by_tier.get('metrics', {})
        metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

        console.print(f'\n[bold]{tier.title()} model:[/bold]')
        for i, (model_id, score) in enumerate(options, 1):
            row = metrics.get(model_id, {})
            has_aa = row.get('intelligence', 0.0) > 0 or row.get('coding', 0.0) > 0
            score_text = f'({score:.1f})' if score else ''
            source = 'AA' if has_aa else 'Inferred'
            console.print(f'  [bold][{i}][/bold] {model_id}  {score_text} [{source}]')

        while True:
            raw = console.input(f'  Select [1-{len(options)}]: ').strip()
            if raw.isdigit():
                index = int(raw)
                if 1 <= index <= len(options):
                    mapping[tier] = options[index - 1][0]
                    break
            console.print(f'  [red]Enter a number 1-{len(options)}.[/red]')

    response = console.input('\nAccept this mapping? [Y/n] ').strip().lower()
    if response in ('n', 'no'):
        return None
    return mapping


def _config_path() -> str:
    return str(GLOBAL_MODELS_PATH)


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync OpenCode model tier mapping using benchmarks')
    add_arguments(parser)
    sys.exit(run(parser.parse_args()))
