import tempfile
from unittest import mock
from click.testing import CliRunner

import pytest

from ubuntu_cloud_image_changelog.cli import generate

@pytest.fixture
def dummy_manifests():
    # Create two temp files with dummy manifest content
    from_manifest = tempfile.NamedTemporaryFile(mode="wb", delete=False)
    to_manifest = tempfile.NamedTemporaryFile(mode="wb", delete=False)

    from_manifest.write(b"dummydeb\t1.0-0\n")
    to_manifest.write(b"dummydeb\t1.0-0\n")

    return from_manifest, to_manifest


@pytest.mark.parametrize(
    'from_series, to_series, from_serial, to_serial, ppas, image_architecture, exit_code',
    [
        ('noble', 'noble', '20250101', '20250202', [], 'amd64', 0),
        ('noble', 'noble', None, '20250202', [], 'amd64', 0),
        ('noble', 'noble', '20250101', None, [], 'amd64', 0),
    ]
)
def test_generate_validate_inputs_and_run(
    dummy_manifests, from_series, to_series, from_serial, to_serial, ppas,
    image_architecture, exit_code
):
    # Dummy manifests from pytest fixture
    from_manifest, to_manifest = dummy_manifests

    with \
        mock.patch("ubuntu_cloud_image_changelog.cli.launchpadagent.get_launchpad") as mock_get_launchpad, \
        mock.patch(
            "ubuntu_cloud_image_changelog.cli.lib.arch_independent_package_name",
            return_value="dummy-package-name-no-arch"
        ), \
        mock.patch(
            "ubuntu_cloud_image_changelog.cli.lib.get_source_package_details",
            return_value=("srcpkg", "1.0-0")
        ), \
        mock.patch(
            "ubuntu_cloud_image_changelog.cli.lib.get_changelog",
            return_value="/tmp/changelog"
        ), \
        mock.patch(
            "ubuntu_cloud_image_changelog.cli.lib.parse_changelog",
            return_value=(False, [])
        ), \
        mock.patch("ubuntu_cloud_image_changelog.cli.click.echo"):

        mock_launchpad = mock.Mock()
        mock_ubuntu = mock.Mock()
        mock_launchpad.distributions = {"ubuntu": mock_ubuntu}
        mock_get_launchpad.return_value = mock_launchpad

        # CliRunner allows invoking a click command for testing purposes
        runner = CliRunner()
        result = runner.invoke(
            generate,
            [
                "--from-series", from_series,
                "--to-series", to_series,
                "--from-serial", from_serial,
                "--to-serial", to_serial,
                "--from-manifest", from_manifest.name,
                "--to-manifest", to_manifest.name,
                "--image-architecture", image_architecture,
                *[f"--ppa={ppa}" for ppa in ppas],
            ]
        )
        assert result.exit_code == exit_code