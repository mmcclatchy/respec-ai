import json
import os
import re
import sys
import urllib.error
import urllib.request
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.table import Table

from src.cli.config.global_config import save_global_models
from src.cli.ui.console import console, print_error, print_info, print_warning


_OPENCODE_GO_URL = 'https://opencode.ai/docs/go/'
_EXA_SEARCH_URL = 'https://api.exa.ai/search'
_MODEL_ID_PATTERN = re.compile(r'opencode-go/[\w.-]+')

_REASONING_SIGNALS = {'aime', 'math', 'swe-bench', 'swe_bench', 'gpqa', 'reasoning', 'competition', 'olympiad'}
_INSTRUCTION_SIGNALS = {'ifeval', 'mt-bench', 'mtbench', 'instruction follow', 'instruction-follow', 'task execution'}
_SPEED_SIGNALS = {'tok/s', 'tokens/s', 'latency', 'throughput', 'fast', 'efficient', 'lightweight'}


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        help='Accept recommended mapping without prompting',
    )
    parser.add_argument(
        '--exa-key',
        help='Exa API key (overrides EXA_API_KEY env var)',
    )


def run(args: Namespace) -> int:
    exa_key = getattr(args, 'exa_key', None) or os.environ.get('EXA_API_KEY', '')

    print_info('Fetching Go Plan models from opencode.ai...')
    models = _fetch_go_plan_models()
    if not models:
        print_error('Could not retrieve Go Plan model list. Check your network connection.')
        return 1

    console.print(f'Found {len(models)} models: {", ".join(m.split("/", 1)[1] for m in models)}')

    if exa_key:
        console.print('Searching recent benchmarks via Exa (last 90 days)...\n')
        evidence = _fetch_benchmark_evidence(models, exa_key)
    else:
        print_warning('EXA_API_KEY not set — using cost-based heuristic (most expensive = most capable)')
        print_warning('Run with --exa-key or set EXA_API_KEY for benchmark-backed recommendations')
        evidence = {}

    ranked = _rank_models(models, evidence)

    _display_evidence_table(evidence)
    _display_tier_table(ranked)

    if not getattr(args, 'yes', False):
        response = console.input('\nAccept this mapping? [Y/n] ')
        if response.strip().lower() in ('n', 'no'):
            print_warning('Mapping not saved')
            return 1

    save_global_models(ranked)
    console.print(
        f'\n[bold green]✓[/bold green] Saved to [cyan]{Path.home() / ".config" / "respec-ai" / "models.json"}[/cyan]'
    )
    print_info("Run 'respec-ai regenerate' to apply new models to opencode.json")
    return 0


def _fetch_go_plan_models() -> list[str]:
    try:
        req = urllib.request.Request(_OPENCODE_GO_URL, headers={'User-Agent': 'respec-ai/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        found = _MODEL_ID_PATTERN.findall(html)
        return list(dict.fromkeys(found))
    except (urllib.error.URLError, OSError):
        return []


def _fetch_benchmark_evidence(models: list[str], exa_key: str) -> dict[str, list[dict[str, str]]]:
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
    evidence: dict[str, list[dict[str, str]]] = {}

    for model_id in models:
        short = model_id.split('/', 1)[1]
        payload = json.dumps(
            {
                'query': f'{short} benchmark coding reasoning performance',
                'numResults': 3,
                'startPublishedDate': cutoff,
                'useAutoprompt': True,
            }
        ).encode()
        req = urllib.request.Request(
            _EXA_SEARCH_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': exa_key,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])
            evidence[model_id] = [
                {
                    'title': r.get('title', ''),
                    'snippet': (r.get('text') or r.get('summary') or '')[:200],
                    'published': (r.get('publishedDate') or '')[:10],
                    'url': r.get('url', ''),
                }
                for r in results
            ]
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            evidence[model_id] = []

    return evidence


def _score_model(model_id: str, results: list[dict[str, str]]) -> tuple[int, int, int]:
    text = ' '.join((r['title'] + ' ' + r['snippet']).lower() for r in results)
    reasoning = sum(1 for s in _REASONING_SIGNALS if s in text)
    instruction = sum(1 for s in _INSTRUCTION_SIGNALS if s in text)
    speed = sum(1 for s in _SPEED_SIGNALS if s in text)
    return reasoning, instruction, speed


def _rank_models(models: list[str], evidence: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    if not evidence:
        tiers = ['opus', 'sonnet', 'haiku']
        return {tier: models[i] for i, tier in enumerate(tiers) if i < len(models)}

    scored = [(m, _score_model(m, evidence.get(m, []))) for m in models]
    by_reasoning = sorted(scored, key=lambda x: x[1][0], reverse=True)
    by_instruction = sorted(scored, key=lambda x: x[1][1], reverse=True)
    by_speed = sorted(scored, key=lambda x: x[1][2], reverse=True)

    opus = by_reasoning[0][0]
    remaining = [m for m, _ in by_instruction if m != opus]
    sonnet = remaining[0] if remaining else (by_instruction[1][0] if len(by_instruction) > 1 else models[1])
    haiku_candidates = [m for m in (m for m, _ in by_speed) if m not in (opus, sonnet)]
    haiku = haiku_candidates[0] if haiku_candidates else None

    result: dict[str, str] = {'opus': opus, 'sonnet': sonnet}
    if haiku:
        result['haiku'] = haiku
    return result


def _key_finding(results: list[dict[str, str]]) -> str:
    if not results:
        return '[dim]no recent data[/dim]'
    first = results[0]
    snippet = first['snippet'].strip()
    return snippet[:60] + '...' if len(snippet) > 60 else snippet or first['title'][:60]


def _display_evidence_table(evidence: dict[str, list[dict[str, str]]]) -> None:
    if not evidence:
        return
    table = Table(title='Benchmark Evidence', show_header=True, header_style='bold cyan')
    table.add_column('Model')
    table.add_column('Key Finding')
    table.add_column('Date')
    for model_id, results in evidence.items():
        short = model_id.split('/', 1)[1]
        date = results[0]['published'] if results else ''
        table.add_row(short, _key_finding(results), date)
    console.print()
    console.print(table)


def _display_tier_table(ranked: dict[str, str]) -> None:
    table = Table(title='Recommended Tier Mapping', show_header=True, header_style='bold cyan')
    table.add_column('Tier')
    table.add_column('Model')
    for tier, model_id in ranked.items():
        table.add_row(tier, model_id)
    console.print()
    console.print(table)


if __name__ == '__main__':
    parser = ArgumentParser(description='Fetch OpenCode Go Plan models and set tier mapping')
    add_arguments(parser)
    sys.exit(run(parser.parse_args()))
