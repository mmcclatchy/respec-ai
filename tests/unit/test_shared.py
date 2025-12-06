"""Tests for state manager factory in shared module."""

import pytest
from pytest import MonkeyPatch

from src.shared import create_state_manager
from src.utils.state_manager import InMemoryStateManager


def test_create_memory_state_manager(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'memory')
    manager = create_state_manager()
    assert isinstance(manager, InMemoryStateManager)


def test_create_memory_state_manager_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv('STATE_MANAGER', raising=False)
    manager = create_state_manager()
    assert isinstance(manager, InMemoryStateManager)


def test_create_memory_state_manager_case_insensitive(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'MEMORY')
    manager = create_state_manager()
    assert isinstance(manager, InMemoryStateManager)


def test_create_database_state_manager_raises(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'database')
    with pytest.raises(NotImplementedError, match='not yet implemented'):
        create_state_manager()


def test_create_database_state_manager_case_insensitive_raises(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'DATABASE')
    with pytest.raises(NotImplementedError, match='not yet implemented'):
        create_state_manager()


def test_create_invalid_state_manager_raises(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'invalid')
    with pytest.raises(ValueError, match='Unknown STATE_MANAGER value'):
        create_state_manager()


def test_create_state_manager_validates_options(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('STATE_MANAGER', 'redis')
    with pytest.raises(ValueError, match='"memory", "database"'):
        create_state_manager()
