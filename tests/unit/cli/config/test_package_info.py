from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from importlib.metadata import PackageNotFoundError as MetadataPackageNotFoundError

from src.cli.config.package_info import (
    PackageInfoError,
    get_package_installation_path,
    get_package_version,
)


class TestGetPackageInstallationPath:
    def test_successful_path_detection(self, mocker: MockerFixture, tmp_path: Path) -> None:
        src_dir = tmp_path / 'src'
        src_dir.mkdir()
        (src_dir / '__init__.py').touch()

        mock_src = mocker.MagicMock()
        mock_src.__file__ = str(src_dir / '__init__.py')

        mocker.patch('src.cli.config.package_info.src', mock_src)
        result = get_package_installation_path()
        assert result == src_dir.resolve()

    def test_import_error(self, mocker: MockerFixture) -> None:
        mock_src = mocker.MagicMock()
        type(mock_src).__file__ = mocker.PropertyMock(side_effect=ImportError('Cannot import'))

        mocker.patch('src.cli.config.package_info.src', mock_src)
        with pytest.raises(PackageInfoError, match='Cannot import src module'):
            get_package_installation_path()


class TestGetPackageVersion:
    def test_successful_version_extraction(self, mocker: MockerFixture) -> None:
        mocker.patch('src.cli.config.package_info.version', return_value='0.4.6')
        result = get_package_version()
        assert result == '0.4.6'

    def test_package_not_found(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.config.package_info.version',
            side_effect=MetadataPackageNotFoundError('respec-ai'),
        )
        with pytest.raises(PackageInfoError, match='respec-ai package not found'):
            get_package_version()

    def test_unexpected_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.config.package_info.version',
            side_effect=RuntimeError('Unexpected error'),
        )
        with pytest.raises(PackageInfoError, match='Error reading package version'):
            get_package_version()
