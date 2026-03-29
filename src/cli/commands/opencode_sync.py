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
_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

_QUALITY_FIELDS = (
    'artificial_analysis_intelligence_index',
    'artificial_analysis_coding_index',
    'artificial_analysis_math_index',
)


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


def run(args: Namespace) -> int:
    aa_key = getattr(args, 'aa_key', None) or os.environ.get('ARTIFICIAL_ANALYSIS_API_KEY', '')

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

    scored = _score_models(models, aa_data)

    if aa_data:
        _display_benchmark_table(scored)

    suggestion = _suggest_tiers(scored)
    _display_suggestion_table(suggestion, scored)

    if getattr(args, 'yes', False):
        mapping = suggestion
    else:
        mapping = _interactive_override(suggestion, models)
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
        models_list = data if isinstance(data, list) else data.get('models', data.get('data', []))
        for model in models_list:
            name = (model.get('name') or model.get('slug') or '').lower()
            if not name:
                continue
            evals = model.get('evaluations') or {}
            scores: dict[str, float] = {}
            for field in _QUALITY_FIELDS:
                val = evals.get(field)
                if val is not None:
                    scores[field] = float(val)
            if scores:
                result[name] = scores
        return result
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        print_warning('Could not fetch Artificial Analysis data — falling back to interactive selection')
        return {}


def _score_models(
    models: list[str],
    aa_data: dict[str, dict[str, float]],
) -> list[tuple[str, float]]:
    scored: list[tuple[str, float]] = []
    for model_id in models:
        short = model_id.split('/', 1)[-1].lower()
        match = _find_aa_match(short, aa_data)
        if match:
            scores = aa_data[match]
            total = sum(scores.get(f, 0.0) for f in _QUALITY_FIELDS)
            scored.append((model_id, total))
        else:
            scored.append((model_id, 0.0))
    return sorted(scored, key=lambda x: x[1], reverse=True)


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


def _suggest_tiers(scored: list[tuple[str, float]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if scored:
        mapping['reasoning'] = scored[0][0]
    if len(scored) >= 2:
        mapping['task'] = scored[1][0]
    elif scored:
        mapping['task'] = scored[0][0]
    return mapping


def _display_benchmark_table(scored: list[tuple[str, float]]) -> None:
    table = Table(title='Benchmark Scores', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Total Score', justify='right')
    for model_id, score in scored:
        short = model_id.split('/', 1)[-1]
        table.add_row(short, f'{score:.1f}' if score else '[dim]no data[/dim]')
    console.print()
    console.print(table)


def _display_suggestion_table(suggestion: dict[str, str], scored: list[tuple[str, float]]) -> None:
    table = Table(title='Recommended Tier Mapping', show_header=True, header_style='bold cyan')
    table.add_column('Tier')
    table.add_column('Model')
    table.add_column('Basis')
    scores_map = dict(scored)
    for tier, model_id in suggestion.items():
        score = scores_map.get(model_id, 0.0)
        basis = f'score {score:.1f}' if score else 'position'
        table.add_row(tier, model_id, basis)
    console.print()
    console.print(table)


def _interactive_override(
    suggestion: dict[str, str],
    models: list[str],
) -> dict[str, str] | None:
    console.print('\n[bold]Confirm or override the suggested mapping:[/bold]')

    mapping: dict[str, str] = {}
    for tier in ('reasoning', 'task'):
        current = suggestion.get(tier, models[0] if models else '')
        response = console.input(f'  {tier} model [{current}]: ').strip()
        mapping[tier] = response if response else current

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
