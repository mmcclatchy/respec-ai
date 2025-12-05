from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.config.package_info import (
    PackageInfoError,
    get_package_installation_path,
    get_package_version,
)


class TestGetPackageInstallationPath:
    def test_successful_path_detection(self, mocker: MockerFixture, tmp_path: Path) -> None:
        services_dir = tmp_path / 'src'
        services_dir.mkdir()
        (services_dir / '__init__.py').touch()
        (tmp_path / 'pyproject.toml').touch()

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(services_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        result = get_package_installation_path()
        assert result == tmp_path.resolve()

    def test_missing_pyproject_toml(self, mocker: MockerFixture, tmp_path: Path) -> None:
        services_dir = tmp_path / 'src'
        services_dir.mkdir()
        (services_dir / '__init__.py').touch()

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(services_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        with pytest.raises(PackageInfoError, match='Cannot determine respec-ai installation path'):
            get_package_installation_path()

    def test_import_error(self, mocker: MockerFixture) -> None:
        mock_src = mocker.MagicMock()
        type(mock_src).__file__ = mocker.PropertyMock(side_effect=ImportError('Cannot import'))

        mocker.patch('src.cli.config.package_info.src', mock_src)
        with pytest.raises(PackageInfoError, match='Cannot import src module'):
            get_package_installation_path()


class TestGetPackageVersion:
    def test_successful_version_extraction(self, mocker: MockerFixture, tmp_path: Path) -> None:
        services_dir = tmp_path / 'src'
        services_dir.mkdir()
        (services_dir / '__init__.py').touch()

        pyproject_content = """[project]
name = "respec-ai"
version = "0.2.0"
description = "Test"
"""
        (tmp_path / 'pyproject.toml').write_text(pyproject_content, encoding='utf-8')

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(services_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        result = get_package_version()
        assert result == '0.2.0'

    def test_version_with_quotes(self, mocker: MockerFixture, tmp_path: Path) -> None:
        services_dir = tmp_path / 'src'
        services_dir.mkdir()
        (services_dir / '__init__.py').touch()

        pyproject_content = """[project]
name = "respec-ai"
version = '1.0.0'
"""
        (tmp_path / 'pyproject.toml').write_text(pyproject_content, encoding='utf-8')

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(services_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        result = get_package_version()
        assert result == '1.0.0'

    def test_missing_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        services_dir = tmp_path / 'src'
        services_dir.mkdir()
        (services_dir / '__init__.py').touch()

        pyproject_content = """[project]
name = "respec-ai"
"""
        (tmp_path / 'pyproject.toml').write_text(pyproject_content, encoding='utf-8')

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(services_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        with pytest.raises(PackageInfoError, match='Version not found in pyproject.toml'):
            get_package_version()
