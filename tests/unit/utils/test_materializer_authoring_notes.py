import pytest

from src.utils.materializers import UNMATERIALIZED_LANGUAGE_NOTE, language_authoring_notes, sentinel_table


@pytest.mark.parametrize('language', sorted(sentinel_table()))
def test_every_registered_language_gets_its_own_authoring_notes_never_the_unmaterialized_note(language: str) -> None:
    notes = language_authoring_notes([language])

    heading = f'#### {language}\n'
    assert notes.startswith(heading)
    section = notes.removeprefix(heading)
    assert section.strip()
    assert UNMATERIALIZED_LANGUAGE_NOTE not in section
