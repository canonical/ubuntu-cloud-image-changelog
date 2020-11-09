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
@click.option(
    "--ppa",
    "ppas",
    required=False,
    multiple=True,
    type=click.STRING,
    help="Packages in manifest are known to have been installed from this PPA."
    "Expected format is "
    "'https://launchpad.net/~%LAUNCHPAD_USERNAME%/+archive/ubuntu/%PPA_NAME%'"
    "Multiple --ppa options can be specified",
)
def main(from_manifest, to_manifest, ppas):
    # type: (Text, Text, List) -> None
    """"""
    from_manifest_lines = from_manifest.readlines()
    to_manifest_lines = to_manifest.readlines()
    from_deb_packages = {}
    to_deb_packages = {}
    from_snap_packages = {}
    to_snap_packages = {}
    snap_package_prefix = "snap:"

    removed_deb_packages = []
    added_deb_packages = []
    deb_package_diffs = {}

    removed_snap_packages = []
    added_snap_packages = []
    snap_package_diffs = {}

    # parse the from manifest
    for from_manifest_line in from_manifest_lines:
        package, *version = from_manifest_line.decode("utf-8").strip().split("\t")
        if package.startswith(snap_package_prefix):
            package = package.replace(snap_package_prefix, "")
            from_snap_packages[package] = version[1]
        else:
            from_deb_packages[package] = version[0]

    # parse the to manifest
    for to_manifest_line in to_manifest_lines:
        package, *version = to_manifest_line.decode("utf-8").strip().split("\t")
        if package.startswith(snap_package_prefix):
            package = package.replace(snap_package_prefix, "")
            to_snap_packages[package] = version[1]
        else:
            to_deb_packages[package] = version[0]

    # Are there any snap package diffs?
    if from_snap_packages or to_snap_packages:

        for package in from_snap_packages.keys():
            if package not in to_snap_packages.keys():
                removed_snap_packages.append(package)

        for package in to_snap_packages.keys():
            if package not in from_snap_packages.keys():
                added_snap_packages.append(package)

        for to_package, to_package_version in to_snap_packages.items():
            # only need to find diff for packages that are not new
            if to_package not in added_snap_packages:
                from_package_version = from_snap_packages[to_package]
                if from_package_version != to_package_version:
                    snap_package_diffs[to_package] = {
                        "from": from_package_version,
                        "to": to_package_version,
                    }

        click.echo("Snap packages added: {}".format(added_snap_packages))
        click.echo("Snap packages removed: {}".format(removed_snap_packages))
        click.echo("Snap packages changed: {}".format(list(snap_package_diffs.keys())))

    # Are there any deb package diffs?
    if from_deb_packages or to_deb_packages:

        for package in from_deb_packages.keys():
            if package not in to_deb_packages.keys():
                removed_deb_packages.append(package)

        for package in to_deb_packages.keys():
            if package not in from_deb_packages.keys():
                added_deb_packages.append(package)

        for to_package, to_package_version in to_deb_packages.items():
            # only need to find diff for packages that are not new
            if to_package not in added_deb_packages:
                from_package_version = from_deb_packages[to_package]
                if from_package_version != to_package_version:
                    deb_package_diffs[to_package] = {
                        "from": from_package_version,
                        "to": to_package_version,
                    }

        click.echo("Deb packages added: {}".format(added_deb_packages))
        click.echo("Deb packages removed: {}".format(removed_deb_packages))
        click.echo("Deb packages changed: {}".format(list(deb_package_diffs.keys())))

    if snap_package_diffs:

        click.echo(
            "\n** Package version diffs for for changed snap packages "
            "below. Full changelog for snap packages are not listed **\n"
        )

        # for each of the snap package diffs list the diff in versions
        for package, from_to in snap_package_diffs.items():
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

    if deb_package_diffs:

        click.echo("\n** Changelogs for added and changed deb packages " "below: **\n")

        # for each of the deb package diffs and new packages download the
        # changelog
        with tempfile.TemporaryDirectory() as tmp_cache_directory:
            for package in added_deb_packages:
                (
                    package_changelog_file,
                    valid_changelog,
                    valid_ppa_changes,
                ) = lib.get_changelog(
                    tmp_cache_directory, package, to_deb_packages[package], ppas
                )
                if valid_changelog:
                    # get the most recent changelog entry
                    version_diff_changelog = lib.parse_changelog(
                        package_changelog_file, count=1
                    )
                elif valid_ppa_changes:
                    # get the most recent changes entry
                    version_diff_changelog = lib.parse_ppa_changes(
                        package_changelog_file
                    )
                else:
                    with open(
                        package_changelog_file, "rb"
                    ) as unparsed_invalid_changelog_file:
                        version_diff_changelog = unparsed_invalid_changelog_file.read()
                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} version {} was added. Below is the most recent changelog entry".format(
                        package, to_deb_packages[package]
                    )
                )
                click.echo()
                click.echo(version_diff_changelog)

            for package, from_to in deb_package_diffs.items():
                (
                    package_changelog_file,
                    valid_changelog,
                    valid_ppa_changes,
                ) = lib.get_changelog(tmp_cache_directory, package, from_to["to"], ppas)
                if valid_changelog:
                    # get changelog just between the from and to version
                    version_diff_changelog = lib.parse_changelog(
                        package_changelog_file, from_to["from"], from_to["to"]
                    )
                elif valid_ppa_changes:
                    # get the most recent changes entry
                    version_diff_changelog = lib.parse_ppa_changes(
                        package_changelog_file
                    )
                else:
                    with open(
                        package_changelog_file, "rb"
                    ) as unparsed_invalid_changelog_file:
                        version_diff_changelog = unparsed_invalid_changelog_file.read()
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
