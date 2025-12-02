"""
Integration test for /specter-spec command with multiple matching specs.
Validates AskUserQuestion integration for spec file selection.
"""

from pathlib import Path

import pytest


def test_multiple_spec_matches_prompts_user_selection(tmp_path: Path) -> None:
    """
    Test that partial spec name matching multiple files triggers interactive selection.

    Setup:
    - Create project with 3 specs matching "phase-2*":
      - phase-2a-neo4j-integration.md
      - phase-2b-exa-api-integration.md
      - phase-2c-lambda-evaluation.md

    Expected:
    - Command calls Glob and finds 3 matches
    - Command uses AskUserQuestion with 3 options
    - User selects option 2 (phase-2b)
    - Command continues with phase-2b-exa-api-integration
    """
    # Create test project structure
    project_dir = tmp_path / '.specter' / 'projects' / 'test-project'
    specs_dir = project_dir / 'specter-specs'
    specs_dir.mkdir(parents=True)

    # Create 3 matching spec files
    spec_files = ['phase-2a-neo4j-integration.md', 'phase-2b-exa-api-integration.md', 'phase-2c-lambda-evaluation.md']

    for spec_file in spec_files:
        spec_path = specs_dir / spec_file
        spec_name = spec_file.replace('.md', '')
        spec_path.write_text(f'# Technical Specification: {spec_name}\n\n## Overview\nTest spec')

    # TODO: Implement command execution with mocked AskUserQuestion
    # - Run: /specter-spec test-project phase-2
    # - Verify: AskUserQuestion called with 3 options
    # - Simulate: User selects "phase-2b-exa-api-integration.md"
    # - Assert: Command uses phase-2b-exa-api-integration as SPEC_NAME

    pytest.skip('Test scaffold created - implementation TODO')


def test_single_spec_match_no_prompt(tmp_path: Path) -> None:
    # Create only 1 spec matching "phase-2a"
    # Verify no AskUserQuestion call
    pytest.skip('Test scaffold created - implementation TODO')


def test_zero_spec_matches_exits_with_error(tmp_path: Path) -> None:
    # Create project with no specs
    # Run: /specter-spec test-project phase-999
    # Verify: Exits with "No specification files found" error
    pytest.skip('Test scaffold created - implementation TODO')
