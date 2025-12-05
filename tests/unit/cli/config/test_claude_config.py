import json
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture
from src.cli.config.claude_config import (
    MCP_SERVER_NAME,
    ClaudeConfigError,
    get_mcp_server_config,
    is_mcp_server_registered,
    load_claude_config,
    register_mcp_server,
    restore_backup,
    save_claude_config,
    unregister_mcp_server,
)


class TestLoadClaudeConfig:
    def test_load_existing_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {'RespecAI': {'command': 'uv'}}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = load_claude_config(config_file)
        assert result == config_data

    def test_load_missing_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        result = load_claude_config(config_file)
        assert result == {'mcpServers': {}}

    def test_load_missing_claude_directory(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'nonexistent' / 'config.json'
        with pytest.raises(ClaudeConfigError, match='Claude Code does not appear to be installed'):
            load_claude_config(config_file)

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_file.write_text('{ invalid json }', encoding='utf-8')

        with pytest.raises(ClaudeConfigError, match='Claude config file is corrupted'):
            load_claude_config(config_file)


class TestSaveClaudeConfig:
    def test_save_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {'RespecAI': {'command': 'uv'}}}

        save_claude_config(config_data, config_file, create_backup=False)

        saved_data = json.loads(config_file.read_text(encoding='utf-8'))
        assert saved_data == config_data

    def test_save_with_backup(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        original_data: dict[str, Any] = {'mcpServers': {}}
        config_file.write_text(json.dumps(original_data), encoding='utf-8')

        new_data = {'mcpServers': {'RespecAI': {'command': 'uv'}}}
        save_claude_config(new_data, config_file, create_backup=True)

        backup_file = config_file.with_suffix('.json.backup')
        assert backup_file.exists()
        backup_data = json.loads(backup_file.read_text(encoding='utf-8'))
        assert backup_data == original_data

    def test_save_invalid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        invalid_data: dict[str, Any] = {'circular': None}
        invalid_data['circular'] = invalid_data

        with pytest.raises(ClaudeConfigError, match='Invalid config structure'):
            save_claude_config(invalid_data, config_file)


class TestIsMcpServerRegistered:
    def test_server_registered(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {MCP_SERVER_NAME: {'command': 'uv'}}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = is_mcp_server_registered(config_file)
        assert result is True

    def test_server_not_registered(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data: dict[str, Any] = {'mcpServers': {}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = is_mcp_server_registered(config_file)
        assert result is False

    def test_error_returns_false(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'nonexistent' / 'config.json'
        result = is_mcp_server_registered(config_file)
        assert result is False


class TestRegisterMcpServer:
    def test_new_registration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch('src.cli.config.claude_config.get_package_version', return_value='0.3.0')
        config_file = tmp_path / 'config.json'
        config_file.write_text('{}', encoding='utf-8')

        result = register_mcp_server(force=False, config_path=config_file)
        assert result is True

        config = json.loads(config_file.read_text(encoding='utf-8'))
        assert MCP_SERVER_NAME in config['mcpServers']
        assert config['mcpServers'][MCP_SERVER_NAME]['command'] == 'docker'
        assert config['mcpServers'][MCP_SERVER_NAME]['args'] == [
            'exec',
            '-i',
            'respec-ai-0.3.0',
            'uv',
            'run',
            'python',
            '-m',
            'src.mcp.server',
        ]

    def test_already_registered_without_force(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch('src.cli.config.claude_config.get_package_version', return_value='0.3.0')
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {MCP_SERVER_NAME: {'command': 'docker'}}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = register_mcp_server(force=False, config_path=config_file)
        assert result is False

    def test_force_reregister(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch('src.cli.config.claude_config.get_package_version', return_value='0.3.0')
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {MCP_SERVER_NAME: {'command': 'old'}}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = register_mcp_server(force=True, config_path=config_file)
        assert result is True

        config = json.loads(config_file.read_text(encoding='utf-8'))
        assert config['mcpServers'][MCP_SERVER_NAME]['command'] == 'docker'
        assert config['mcpServers'][MCP_SERVER_NAME]['args'] == [
            'exec',
            '-i',
            'respec-ai-0.3.0',
            'uv',
            'run',
            'python',
            '-m',
            'src.mcp.server',
        ]


class TestUnregisterMcpServer:
    def test_successful_unregister(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data = {'mcpServers': {MCP_SERVER_NAME: {'command': 'uv'}}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = unregister_mcp_server(config_file)
        assert result is True

        config = json.loads(config_file.read_text(encoding='utf-8'))
        assert MCP_SERVER_NAME not in config['mcpServers']

    def test_not_registered(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data: dict[str, Any] = {'mcpServers': {}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = unregister_mcp_server(config_file)
        assert result is False


class TestRestoreBackup:
    def test_successful_restore(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        backup_file = config_file.with_suffix('.json.backup')

        original_data = {'mcpServers': {'original': True}}
        corrupted_data = {'corrupted': True}

        backup_file.write_text(json.dumps(original_data), encoding='utf-8')
        config_file.write_text(json.dumps(corrupted_data), encoding='utf-8')

        restore_backup(config_file)

        restored_data = json.loads(config_file.read_text(encoding='utf-8'))
        assert restored_data == original_data

    def test_missing_backup(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'

        with pytest.raises(ClaudeConfigError, match='No backup file found'):
            restore_backup(config_file)


class TestGetMcpServerConfig:
    def test_get_existing_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        server_config = {'command': 'uv', 'args': ['run', 'respec-server']}
        config_data = {'mcpServers': {MCP_SERVER_NAME: server_config}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = get_mcp_server_config(config_file)
        assert result == server_config

    def test_get_missing_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.json'
        config_data: dict[str, Any] = {'mcpServers': {}}
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        result = get_mcp_server_config(config_file)
        assert result is None

    def test_error_returns_none(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'nonexistent' / 'config.json'
        result = get_mcp_server_config(config_file)
        assert result is None
