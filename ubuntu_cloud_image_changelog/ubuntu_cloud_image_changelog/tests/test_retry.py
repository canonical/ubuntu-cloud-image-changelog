import unittest.mock as mock

import pytest

from ubuntu_cloud_image_changelog import lib


def test_retry_first_try():
    """Retry only retry on failure."""
    arg = object()
    return_value = object()
    fn = mock.MagicMock(side_effect=lambda _: return_value)

    with mock.patch("time.sleep") as mock_sleep:
        result = lib.retry(fn)(arg)

    fn.assert_called_once_with(arg)
    assert result is return_value
    mock_sleep.assert_not_called()


def test_retry_raises():
    """Retry raises the last error after exhaustion."""

    class MyError(Exception):
        pass

    arg = object()
    fn = mock.MagicMock(side_effect=MyError)

    with mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(MyError):
            lib.retry(fn, num_attempts=3)(arg)

    assert fn.mock_calls == [mock.call(arg)] * 3
    assert mock_sleep.mock_calls == [mock.call(0), mock.call(1), mock.call(2)]
