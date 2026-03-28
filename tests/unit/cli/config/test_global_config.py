import json
from pathlib import Path
from unittest.mock import patch

from src.cli.config.global_config import load_global_models, save_global_models


class TestLoadGlobalModels:
    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', tmp_path / 'models.json'):
            assert load_global_models() == {}

    def test_returns_opencode_section(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(
            json.dumps({'opencode': {'opus': 'opencode-go/kimi-k2.5', 'sonnet': 'opencode-go/minimax-m2.7'}}),
            encoding='utf-8',
        )
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            result = load_global_models()
        assert result == {'opus': 'opencode-go/kimi-k2.5', 'sonnet': 'opencode-go/minimax-m2.7'}

    def test_returns_empty_when_no_opencode_key(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(json.dumps({'other': {}}), encoding='utf-8')
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            assert load_global_models() == {}

    def test_returns_empty_on_corrupt_json(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text('not json', encoding='utf-8')
        with patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path):
            assert load_global_models() == {}


class TestSaveGlobalModels:
    def test_creates_directory_and_file(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'sub' / 'models.json'
        with (
            patch('src.cli.config.global_config.GLOBAL_CONFIG_DIR', tmp_path / 'sub'),
            patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path),
        ):
            save_global_models({'opus': 'opencode-go/kimi-k2.5'})
        assert models_path.exists()
        data = json.loads(models_path.read_text())
        assert data['opencode'] == {'opus': 'opencode-go/kimi-k2.5'}

    def test_preserves_existing_non_opencode_keys(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(json.dumps({'other_key': 'other_value'}), encoding='utf-8')
        with (
            patch('src.cli.config.global_config.GLOBAL_CONFIG_DIR', tmp_path),
            patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path),
        ):
            save_global_models({'opus': 'opencode-go/kimi-k2.5'})
        data = json.loads(models_path.read_text())
        assert data['other_key'] == 'other_value'
        assert data['opencode'] == {'opus': 'opencode-go/kimi-k2.5'}

    def test_overwrites_existing_opencode_section(self, tmp_path: Path) -> None:
        models_path = tmp_path / 'models.json'
        models_path.write_text(json.dumps({'opencode': {'opus': 'old-model'}}), encoding='utf-8')
        with (
            patch('src.cli.config.global_config.GLOBAL_CONFIG_DIR', tmp_path),
            patch('src.cli.config.global_config.GLOBAL_MODELS_PATH', models_path),
        ):
            save_global_models({'opus': 'opencode-go/kimi-k2.5', 'sonnet': 'opencode-go/minimax-m2.7'})
        data = json.loads(models_path.read_text())
        assert data['opencode']['opus'] == 'opencode-go/kimi-k2.5'
        assert data['opencode']['sonnet'] == 'opencode-go/minimax-m2.7'
