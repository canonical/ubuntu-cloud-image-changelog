import tempfile
import unittest.mock as mock
from unittest.mock import call

import pytest

from ubuntu_cloud_image_changelog import lib


def test_get_source_package_retry():
    """Archive package queries should retry on server error"""
    mock_launchpad = mock.MagicMock()
    mock_ubuntu = mock_launchpad.distributions["ubuntu"]

    mock_ubuntu.main_archive.getPublishedBinaries.side_effect = Exception
    with mock.patch("time.sleep"):
        with pytest.raises(Exception):
            lib.get_source_package_details(
                mock_ubuntu,
                mock_launchpad,
                "noble",
                "sl",
                "1.0",
                [],
            )
    expected_calls = [
        call(
            exact_match=True,
            binary_name="sl",
            distro_arch_series="noble",
            order_by_date=True,
            version="1.0",
        )
    ] * 5
    calls = mock_ubuntu.main_archive.getPublishedBinaries.mock_calls
    assert calls == expected_calls


def test_get_changelog_retry():
    """Archive sources queries should retry on server error"""
    mock_launchpad = mock.MagicMock()
    mock_ubuntu = mock_launchpad.distributions["ubuntu"]
    mock_ubuntu.main_archive.getPublishedSources.side_effect = Exception

    with mock.patch("time.sleep"):
        with tempfile.TemporaryDirectory() as cache_dir:
            with pytest.raises(Exception):
                lib.get_changelog(
                    mock_launchpad,
                    mock_ubuntu,
                    "noble",
                    cache_dir,
                    "sl",
                    "1.0",
                    [],
                )
    expected_calls = [
        call(
            exact_match=True,
            source_name="sl",
            distro_series="noble",
            order_by_date=True,
            version="1.0",
        )
    ] * 5
    calls = mock_ubuntu.main_archive.getPublishedSources.mock_calls
    assert calls == expected_calls
