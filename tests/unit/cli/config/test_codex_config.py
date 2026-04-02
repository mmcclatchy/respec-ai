from pathlib import Path
from unittest.mock import patch

from src.cli.config.codex_config import (
    codex_config_path,
    codex_home,
    is_mcp_server_registered,
    load_codex_config,
    register_mcp_server,
    unregister_all_respec_servers,
    unregister_mcp_server,
)


class TestCodexConfig:
    def test_codex_home_uses_env_override(self, tmp_path: Path) -> None:
        with patch.dict('os.environ', {'CODEX_HOME': str(tmp_path / '.codex')}, clear=False):
            assert codex_home() == tmp_path / '.codex'
            assert codex_config_path() == tmp_path / '.codex' / 'config.toml'

    def test_load_config_empty_when_missing(self, tmp_path: Path) -> None:
        path = tmp_path / 'missing.toml'
        assert load_codex_config(path) == {}

    def test_register_and_unregister_round_trip(self, tmp_path: Path) -> None:
        codex_home_path = tmp_path / '.codex'
        with patch.dict('os.environ', {'CODEX_HOME': str(codex_home_path)}, clear=False):
            assert register_mcp_server() is True
            assert is_mcp_server_registered() is True
            assert unregister_mcp_server() is True
            assert is_mcp_server_registered() is False

    def test_unregister_all_removes_aliases(self, tmp_path: Path) -> None:
        codex_home_path = tmp_path / '.codex'
        codex_home_path.mkdir(parents=True)
        config = codex_home_path / 'config.toml'
        config.write_text(
            '[mcp_servers.respec-ai]\ncommand = "respec-ai"\nargs = ["mcp-server"]\n\n'
            '[mcp_servers.respec_ai]\ncommand = "respec-ai"\nargs = ["mcp-server"]\n\n'
            '[mcp_servers.respecai]\ncommand = "respec-ai"\nargs = ["mcp-server"]\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'CODEX_HOME': str(codex_home_path)}, clear=False):
            assert unregister_all_respec_servers() == 3
            content = config.read_text(encoding='utf-8')
            assert 'respec-ai' not in content
            assert 'respec_ai' not in content
            assert 'respecai' not in content
