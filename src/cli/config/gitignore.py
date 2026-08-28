from pathlib import Path

RESPEC_AI_GITIGNORE_ENTRIES: tuple[str, ...] = ('.respec-ai/run/',)


def ensure_gitignore_entries(project_path: Path, entries: tuple[str, ...] = RESPEC_AI_GITIGNORE_ENTRIES) -> None:
    gitignore_path = project_path / '.gitignore'
    existing_lines = gitignore_path.read_text(encoding='utf-8').splitlines() if gitignore_path.exists() else []
    missing = [entry for entry in entries if entry not in existing_lines]
    if not missing:
        return

    with gitignore_path.open('a', encoding='utf-8') as f:
        if existing_lines and existing_lines[-1] != '':
            f.write('\n')
        for entry in missing:
            f.write(f'{entry}\n')
