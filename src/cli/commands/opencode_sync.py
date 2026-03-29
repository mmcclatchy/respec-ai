import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.table import Table

from src.cli.config.global_config import save_global_models
from src.cli.ui.console import console, print_error, print_info, print_warning


_AA_MODELS_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'
_EXA_CONTENTS_URL = 'https://api.exa.ai/contents'
_OPENCODE_GO_DOCS_URL = 'https://opencode.ai/docs/go/'
_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

_REASONING_WEIGHTS: dict[str, float] = {
    'artificial_analysis_intelligence_index': 0.50,
    'artificial_analysis_math_index': 0.35,
    'artificial_analysis_coding_index': 0.15,
}

_TASK_WEIGHTS: dict[str, float] = {
    'artificial_analysis_coding_index': 0.55,
    'artificial_analysis_intelligence_index': 0.25,
    'artificial_analysis_math_index': 0.20,
}


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


def run(args: Namespace) -> int:
    aa_key = getattr(args, 'aa_key', None) or os.environ.get('ARTIFICIAL_ANALYSIS_API_KEY', '')
    exa_key = getattr(args, 'exa_key', None) or os.environ.get('EXA_API_KEY', '')

    provider, models = _discover_models()
    if not models:
        print_error('No OpenCode models found. Ensure opencode is installed and configured.')
        return 1

    console.print(f'Provider: [cyan]{provider}[/cyan]')
    console.print(f'Available models: {", ".join(models)}\n')

    if aa_key:
        print_info('Fetching benchmark data from Artificial Analysis...')
        aa_data = _fetch_aa_data(aa_key)
    else:
        print_warning('ARTIFICIAL_ANALYSIS_API_KEY not set — skipping benchmark lookup')
        print_warning('Set ARTIFICIAL_ANALYSIS_API_KEY or use --aa-key for benchmark-backed recommendations')
        aa_data = {}

    rate_limits: dict[str, str] = {}
    if exa_key:
        rate_limits = _fetch_rate_limits(exa_key, provider)

    scored_by_tier = _score_models_by_tier(models, aa_data)

    if aa_data:
        _display_tier_table('Reasoning Scores', scored_by_tier['reasoning'], rate_limits)
        _display_tier_table('Task Scores', scored_by_tier['task'], rate_limits)

    suggestion = _suggest_tiers(scored_by_tier)
    _display_suggestion_table(suggestion, scored_by_tier)

    if getattr(args, 'yes', False):
        mapping = suggestion
    else:
        mapping = _interactive_override(suggestion, scored_by_tier)
        if mapping is None:
            print_warning('Mapping not saved')
            return 1

    save_global_models(mapping)
    console.print(f'\n[bold green]✓[/bold green] Saved to [cyan]{_config_path()}[/cyan]')
    print_info("Run 'respec-ai regenerate' to apply new models to your config")
    return 0


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


def _fetch_aa_data(aa_key: str) -> dict[str, dict[str, float]]:
    req = urllib.request.Request(
        _AA_MODELS_URL,
        headers={'x-api-key': aa_key, 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result: dict[str, dict[str, float]] = {}
        all_fields = set(_REASONING_WEIGHTS) | set(_TASK_WEIGHTS)
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
        return result
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        print_warning('Could not fetch Artificial Analysis data — falling back to interactive selection')
        return {}


def _fetch_rate_limits(exa_key: str, provider: str) -> dict[str, str]:
    payload = json.dumps(
        {
            'ids': [_OPENCODE_GO_DOCS_URL],
            'text': True,
        }
    ).encode()
    req = urllib.request.Request(
        _EXA_CONTENTS_URL,
        data=payload,
        headers={
            'x-api-key': exa_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = data.get('results', [])
        if not results:
            return {}
        text = results[0].get('text', '')
        return _parse_rate_limits_table(text, provider)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError, IndexError):
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


def _weighted_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    return sum(scores.get(field, 0.0) * weight for field, weight in weights.items())


def _score_models_by_tier(
    models: list[str],
    aa_data: dict[str, dict[str, float]],
) -> dict[str, list[tuple[str, float]]]:
    reasoning_scored: list[tuple[str, float]] = []
    task_scored: list[tuple[str, float]] = []
    for model_id in models:
        short = model_id.split('/', 1)[-1].lower()
        match = _find_aa_match(short, aa_data)
        if match:
            scores = aa_data[match]
            reasoning_scored.append((model_id, _weighted_score(scores, _REASONING_WEIGHTS)))
            task_scored.append((model_id, _weighted_score(scores, _TASK_WEIGHTS)))
        else:
            reasoning_scored.append((model_id, 0.0))
            task_scored.append((model_id, 0.0))
    return {
        'reasoning': sorted(reasoning_scored, key=lambda x: x[1], reverse=True),
        'task': sorted(task_scored, key=lambda x: x[1], reverse=True),
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
    task = scored_by_tier.get('task', [])
    if reasoning:
        mapping['reasoning'] = reasoning[0][0]
    if task:
        mapping['task'] = task[0][0]
    elif reasoning:
        mapping['task'] = reasoning[0][0]
    return mapping


def _display_tier_table(
    title: str,
    scored: list[tuple[str, float]],
    rate_limits: dict[str, str],
) -> None:
    table = Table(title=title, show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Score', justify='right')
    if rate_limits:
        table.add_column('Reqs/5hr', justify='right')
    for model_id, score in scored:
        short = model_id.split('/', 1)[-1]
        score_text = f'{score:.1f}' if score else '[dim]no data[/dim]'
        if rate_limits:
            rate = rate_limits.get(model_id, '\u2014')
            table.add_row(short, score_text, rate)
        else:
            table.add_row(short, score_text)
    console.print()
    console.print(table)


def _display_suggestion_table(
    suggestion: dict[str, str],
    scored_by_tier: dict[str, list[tuple[str, float]]],
) -> None:
    table = Table(title='Recommended Tier Mapping', show_header=True, header_style='bold cyan')
    table.add_column('Tier')
    table.add_column('Model')
    table.add_column('Basis')
    for tier, model_id in suggestion.items():
        tier_scores = dict(scored_by_tier.get(tier, []))
        score = tier_scores.get(model_id, 0.0)
        basis = f'score {score:.1f}' if score else 'position'
        table.add_row(tier, model_id, basis)
    console.print()
    console.print(table)


def _interactive_override(
    suggestion: dict[str, str],
    scored_by_tier: dict[str, list[tuple[str, float]]],
) -> dict[str, str] | None:
    mapping: dict[str, str] = {}

    for tier in ('reasoning', 'task'):
        options = scored_by_tier.get(tier, [])
        suggested = suggestion.get(tier, '')

        console.print(f'\n[bold]{tier.title()} model:[/bold]')
        default_num = 1
        for i, (model_id, score) in enumerate(options, 1):
            suffix = '  [cyan]\u2190 suggested[/cyan]' if model_id == suggested else ''
            score_text = f'({score:.1f})' if score else ''
            console.print(f'  [bold][{i}][/bold] {model_id}  {score_text}{suffix}')
            if model_id == suggested:
                default_num = i

        while True:
            raw = console.input(f'  Select [{default_num}]: ').strip()
            if not raw:
                mapping[tier] = options[default_num - 1][0] if options else suggested
                break
            if raw.isdigit():
                index = int(raw)
                if 1 <= index <= len(options):
                    mapping[tier] = options[index - 1][0]
                    break
                console.print(f'  [red]Invalid number. Enter 1-{len(options)}.[/red]')
                continue
            console.print(f'  [red]Invalid number. Enter 1-{len(options)}.[/red]')

    response = console.input('\nAccept this mapping? [Y/n] ').strip().lower()
    if response in ('n', 'no'):
        return None
    return mapping


def _config_path() -> str:
    return str(Path.home() / '.config' / 'respec-ai' / 'models.json')


if __name__ == '__main__':
    parser = ArgumentParser(description='Sync OpenCode model tier mapping using benchmarks')
    add_arguments(parser)
    sys.exit(run(parser.parse_args()))
