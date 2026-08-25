import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.utils.design_conformance import RecordedDeviation, classify_conformance


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--project-root',
        default='.',
        help='Project root the Skeleton Index paths are relative to (defaults to cwd)',
    )


def run(args: Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    payload = json.loads(sys.stdin.read())

    skeleton_index_text = payload.get('skeleton_index_text', '')
    deviations = tuple(
        RecordedDeviation(qualified_name=d['qualified_name'], reason=d['reason'])
        for d in payload.get('deviations', [])
    )

    report = classify_conformance(project_root, skeleton_index_text, deviations)

    output = {
        'blockers': [
            {'qualified_name': b.qualified_name, 'kind': b.kind, 'detail': b.detail} for b in report.blockers
        ],
        'findings': [
            {'qualified_name': f.qualified_name, 'kind': f.kind, 'detail': f.detail} for f in report.findings
        ],
        'updated_skeleton_index': report.updated_skeleton_index,
        'new_settled_decisions': report.new_settled_decisions,
    }
    print(json.dumps(output))
    return 0
