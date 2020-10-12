"""Console script for ubuntu_cloud_image_changelog."""
import os
import sys
import tempfile
import click

from ubuntu_cloud_image_changelog import lib


@click.command()
@click.option(
    "--from-manifest",
    required=True,
    type=click.File("rb"),
    help="From manifest."
    "{}".format(
        "When using the ubuntu-cloud-image-changelog "
        "snap this config must reside under $HOME."
        if os.environ.get("SNAP", None)
        else ""
    ),
)
@click.option(
    "--to-manifest",
    required=True,
    type=click.File("rb"),
    help="From manifest."
    "{}".format(
        "When using the ubuntu-cloud-image-changelog "
        "snap this config must reside under $HOME."
        if os.environ.get("SNAP", None)
        else ""
    ),
)
def main(from_manifest, to_manifest):
    # type: (Text, Text) -> None
    """"""
    from_manifest_lines = from_manifest.readlines()
    to_manifest_lines = to_manifest.readlines()
    from_packages = {}
    to_packages = {}
    for from_manifest_line in from_manifest_lines:
        package, version = from_manifest_line.decode("utf-8").strip().split("\t")
        from_packages[package] = version
    for to_manifest_line in to_manifest_lines:
        package, version = to_manifest_line.decode("utf-8").strip().split("\t")
        to_packages[package] = version

    removed_packages = []
    added_packages = []

    for package in from_packages.keys():
        if package not in to_packages.keys():
            removed_packages.append(package)

    for package in to_packages.keys():
        if package not in from_packages.keys():
            added_packages.append(package)

    package_diffs = {}
    for to_package, to_package_version in to_packages.items():
        # only need to find diff for packages that are not new
        if to_package not in added_packages:
            from_package_version = from_packages[to_package]
            if from_package_version != to_package_version:
                package_diffs[to_package] = {
                    "from": from_package_version,
                    "to": to_package_version,
                }

    click.echo("Packages added: {}".format(added_packages))
    click.echo("Packages removed: {}".format(removed_packages))
    click.echo("Packages changed: {}".format(list(package_diffs.keys())))

    # for each of the package diffs download the changelog
    with tempfile.TemporaryDirectory() as tmp_cache_directory:
        for package, from_to in package_diffs.items():
            package_changelog_file = lib.get_changelog(
                tmp_cache_directory, package, from_to["to"]
            )
            # get changelog just between the from and to version
            version_diff_changelog = lib.parse_changelog(
                package_changelog_file, from_to["from"], from_to["to"]
            )
            click.echo(
                "==========================================================="
                "==========================================================="
            )
            click.echo(
                "{} changed from version '{}' to version '{}'".format(
                    package, from_to["from"], from_to["to"]
                )
            )
            click.echo()
            click.echo(version_diff_changelog)


if __name__ == "__main__":
    sys.exit(main())
