import unittest.mock as mock
from unittest.mock import call

import pytest

from ubuntu_cloud_image_changelog import lib


def test_get_cve_details_retry():
    fake_url = "https://git.launchpad.net/ubuntu-cve-tracker/plain/active/somecve"
    _mock_launchpad = mock.MagicMock()
    _mock_launchpad._browser.get.side_effect = mock.Mock(side_effect=Exception("Test"))
    with mock.patch("time.sleep"):
        with pytest.raises(Exception):
            lib._get_cve_details("somecve", _mock_launchpad)
    calls = [call(fake_url), call(fake_url), call(fake_url), call(fake_url), call(fake_url)]
    _mock_launchpad._browser.get.assert_called()
    _mock_launchpad._browser.get.assert_has_calls(calls)
