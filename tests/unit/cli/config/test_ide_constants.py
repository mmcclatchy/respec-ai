from pathlib import Path

from src.cli.config.ide_constants import (
    IDE_AGENTS_DIR,
    IDE_COMMANDS_DIR,
    IDE_CONFIG_PATH,
    IDE_NAME,
    MCP_SERVER_NAME,
    get_agents_dir,
    get_commands_dir,
    get_ide_config_path,
    get_mcp_server_name,
)


class TestIdeConstants:
    def test_ide_name(self) -> None:
        assert IDE_NAME == 'claude-code'

    def test_ide_config_path(self) -> None:
        assert IDE_CONFIG_PATH == Path.home() / '.claude' / 'config.json'

    def test_ide_commands_dir(self) -> None:
        assert IDE_COMMANDS_DIR == '.claude/commands'

    def test_ide_agents_dir(self) -> None:
        assert IDE_AGENTS_DIR == '.claude/agents'

    def test_mcp_server_name(self) -> None:
        assert MCP_SERVER_NAME == 'respec-ai'


class TestGetCommandsDir:
    def test_returns_correct_path(self, tmp_path: Path) -> None:
        result = get_commands_dir(tmp_path)
        assert result == tmp_path / '.claude' / 'commands'

    def test_preserves_project_path(self) -> None:
        project = Path('/some/project/path')
        result = get_commands_dir(project)
        assert result == project / '.claude' / 'commands'


class TestGetAgentsDir:
    def test_returns_correct_path(self, tmp_path: Path) -> None:
        result = get_agents_dir(tmp_path)
        assert result == tmp_path / '.claude' / 'agents'

    def test_preserves_project_path(self) -> None:
        project = Path('/some/project/path')
        result = get_agents_dir(project)
        assert result == project / '.claude' / 'agents'


class TestGetIdeConfigPath:
    def test_returns_config_path(self) -> None:
        result = get_ide_config_path()
        assert result == Path.home() / '.claude' / 'config.json'


class TestGetMcpServerName:
    def test_returns_server_name(self) -> None:
        result = get_mcp_server_name()
        assert result == 'respec-ai'
