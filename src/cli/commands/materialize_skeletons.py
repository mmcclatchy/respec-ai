import json
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.ui.console import print_error
from src.utils.skeleton_generator import (
    SkeletonPathEscapesProjectError,
    generate_skeletons,
    generate_tests,
    merge_new_members,
    parse_skeleton_index,
    parse_test_list,
)


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--skeleton-index-file',
        required=True,
        help='Path to a file containing the Phase "### Skeleton Index" markdown content',
    )
    parser.add_argument(
        '--test-list-file',
        required=True,
        help='Path to a file containing the Phase "### Test List" markdown content',
    )
    parser.add_argument(
        '--merge-paths',
        default='',
        help=(
            'Comma-separated Skeleton Index paths the user chose to merge into: only '
            'genuinely new members are appended, existing members are left untouched'
        ),
    )


def run(args: Namespace) -> int:
    project_path = Path.cwd().resolve()
    index_text = Path(args.skeleton_index_file).read_text(encoding='utf-8')
    merge_paths = frozenset(p.strip() for p in args.merge_paths.split(',') if p.strip())

    try:
        index_entries = parse_skeleton_index(index_text)

        # A merge call always follows a prior create-only call for the same index (the
        # conflicting paths were already reported by it). Re-running generate_skeletons
        # here would re-report paths written by that first call as new conflicts, since
        # they now exist on disk -- so a merge call does merging only, nothing else.
        if merge_paths:
            merge_result = merge_new_members(project_path, index_entries, merge_paths)
            output = {
                'written_skeletons': [],
                'written_tests': [],
                'skipped_existing_tests': [],
                'merged_paths': [str(p.relative_to(project_path)) for p in merge_result.merged_paths],
                'unresolved_signature_conflicts': list(merge_result.unresolved_signature_conflicts),
                'reconciliation_needed': [],
            }
        else:
            test_text = Path(args.test_list_file).read_text(encoding='utf-8')
            skeleton_result = generate_skeletons(project_path, index_entries)
            test_result = generate_tests(project_path, parse_test_list(test_text))
            output = {
                'written_skeletons': [str(p.relative_to(project_path)) for p in skeleton_result.written_paths],
                'written_tests': [str(p.relative_to(project_path)) for p in test_result.written_paths],
                'skipped_existing_tests': [
                    str(p.relative_to(project_path)) for p in test_result.skipped_existing
                ],
                'merged_paths': [],
                'unresolved_signature_conflicts': [],
                'reconciliation_needed': [
                    {
                        'path': choice.path,
                        'existing_signatures': list(choice.existing_signatures),
                        'designed_signatures': list(choice.designed_signatures),
                    }
                    for choice in skeleton_result.reconciliation_needed
                ],
            }
    except SkeletonPathEscapesProjectError as e:
        print_error(str(e))
        return 1

    print(json.dumps(output))
    return 0
