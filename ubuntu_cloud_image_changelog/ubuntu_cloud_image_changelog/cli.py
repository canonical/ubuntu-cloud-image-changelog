"""Console script for ubuntu_cloud_image_changelog."""
import os
import sys
import tempfile
import click
import json
from ubuntu_cloud_image_changelog import launchpadagent

from ubuntu_cloud_image_changelog import lib


@click.command()
@click.option(
    "--lp-credentials-store",
    envvar="LP_CREDENTIALS_STORE",
    required=False,
    help="An optional path to an already configured launchpad credentials store.",
    default=None,
)
@click.option(
    "--from-series", help='the Ubuntu series eg. "20.04" or "focal"', required=True
)
@click.option(
    "--to-series", help='the Ubuntu series eg. "20.04" or "focal"', required=True
)
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
    "'%LAUNCHPAD_USERNAME%/%PPA_NAME%' eg. philroche/cloud-init"
    "Multiple --ppa options can be specified",
)
@click.option(
    "--image-architecture",
    help="The architecture of the image to use when querying package "
    "version in the archive/ppa. The default is amd64",
    default="amd64",
    show_default=True,
)
@click.option(
    "--highlight-cves",
    help="Highlight the CVEs referenced in each individual changelog entry"
    ". Default: %(default)s",
    is_flag=True,
    default=False,
)
@click.option(
    "--output-json",
    help="Output the changelog in JSON format to the specified file",
    type=click.Path(exists=False, dir_okay=False, writable=True),
    default=None,
)
@click.option(
    "--output-json-pretty",
    help="Output the JSON changelog in a human readable format. "
    "This option is ignored if `--output-json` is not specified.",
    is_flag=True,
    default=False,
)
def main(
    lp_credentials_store,
    from_series,
    to_series,
    from_manifest,
    to_manifest,
    ppas,
    image_architecture,
    highlight_cves,
    output_json,
    output_json_pretty,
):
    # type: (Text, Text, Text, Text, Text, List, bool, bool, Text, bool) -> None
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

    # Store all changleog items in a dict so we can output in different formats and not just txt.
    changelog = {
        "summary": {},
        "diff": {"deb": {}, "snap": {}},
        "added": {"deb": {}, "snap": {}},
        "removed": {"deb": {}, "snap": {}},
    }
    # parse the from manifest
    for from_manifest_line in from_manifest_lines:
        package, *version = from_manifest_line.decode("utf-8").strip().split("\t")
        if package.startswith(snap_package_prefix):
            package = package.replace(snap_package_prefix, "")
            from_snap_packages[package] = version[1]
        else:
            # packages ending with ':amd64' or ':arm64' are special
            package = lib.arch_independent_package_name(package)
            from_deb_packages[package] = version[0]

    # parse the to manifest
    for to_manifest_line in to_manifest_lines:
        package, *version = to_manifest_line.decode("utf-8").strip().split("\t")
        if package.startswith(snap_package_prefix):
            package = package.replace(snap_package_prefix, "")
            to_snap_packages[package] = version[1]
        else:
            # packages ending with ':amd64' or ':arm64' are special
            package = lib.arch_independent_package_name(package)
            to_deb_packages[package] = version[0]

    # Are there any snap package diffs?
    if from_snap_packages or to_snap_packages:

        for package, version in from_snap_packages.items():
            if package not in to_snap_packages.keys():
                removed_snap_packages.append(package)
                changelog["removed"]["snap"][package] = {
                    "from": {"version": version},
                    "to": {"version": None},
                }

        for package, version in to_snap_packages.items():
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
        changelog["summary"]["snap"] = {
            "added": added_snap_packages,
            "removed": removed_snap_packages,
            "diff": list(snap_package_diffs.keys()),
        }
        click.echo("Snap packages added: {}".format(added_snap_packages))
        click.echo("Snap packages removed: {}".format(removed_snap_packages))
        click.echo("Snap packages changed: {}".format(list(snap_package_diffs.keys())))

    # Are there any deb package diffs?
    if from_deb_packages or to_deb_packages:

        for package, version in from_deb_packages.items():
            if package not in to_deb_packages.keys():
                removed_deb_packages.append(package)
                changelog["removed"]["deb"][package] = {
                    "from": {"version": version},
                    "to": {"version": None},
                }

        for package, version in to_deb_packages.items():
            if package not in from_deb_packages.keys():
                added_deb_packages.append(package)
                changelog["added"]["deb"][package] = {
                    "from": {"version": None},
                    "to": {"version": version},
                }

        for to_package, to_package_version in to_deb_packages.items():
            # only need to find diff for packages that are not new
            if to_package not in added_deb_packages:
                from_package_version = from_deb_packages[to_package]
                if from_package_version != to_package_version:
                    deb_package_diffs[to_package] = {
                        "from": from_package_version,
                        "to": to_package_version,
                    }
        changelog["summary"]["deb"] = {
            "added": added_deb_packages,
            "removed": removed_deb_packages,
            "diff": list(deb_package_diffs.keys()),
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

            changelog["diff"]["snap"][package] = {
                "from": from_to["from"],
                "to": from_to["to"],
            }

            click.echo()

    if deb_package_diffs or added_deb_packages:

        click.echo("\n** Changelogs for added and changed deb packages " "below: **\n")

        # for each of the deb package diffs and new packages download the
        # changelog
        with tempfile.TemporaryDirectory(
            prefix="ubuntu-cloud-image-changelog"
        ) as tmp_cache_directory:
            launchpad = launchpadagent.get_launchpad(
                launchpadlib_dir=tmp_cache_directory,
                lp_credentials_store=lp_credentials_store,
            )
            ubuntu = launchpad.distributions["ubuntu"]
            to_lp_series = ubuntu.getSeries(name_or_version=to_series)
            from_lp_series = ubuntu.getSeries(name_or_version=from_series)
            to_lp_arch_series = to_lp_series.getDistroArchSeries(
                archtag=image_architecture
            )
            from_lp_arch_series = from_lp_series.getDistroArchSeries(
                archtag=image_architecture
            )
            for package in added_deb_packages:
                (
                    to_source_package_name,
                    to_source_package_version,
                ) = lib.get_source_package_details(
                    ubuntu,
                    launchpad,
                    to_lp_arch_series,
                    package,
                    to_deb_packages[package],
                    ppas,
                )
                package_changelog_file = lib.get_changelog(
                    launchpad,
                    ubuntu,
                    to_lp_series,
                    tmp_cache_directory,
                    to_source_package_name,
                    to_source_package_version,
                    ppas,
                )

                # get the three most recent changelog entries
                (
                    version_diff_changelog,
                    cves_referenced,
                    version_diff_changelogs,
                ) = lib.parse_changelog(
                    launchpad,
                    package_changelog_file,
                    to_version=to_source_package_version,
                    count=3,
                    highlight_cves=highlight_cves,
                )

                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} version '{}' (source package {} version '{}') was added. Below are the three most recent changelog entries".format(
                        package,
                        to_deb_packages[package],
                        to_source_package_name,
                        to_source_package_version,
                    )
                )
                changelog["added"]["deb"][package] = {
                    "from": {
                        "source_package_name": None,
                        "source_package_version": None,
                        "version": None,
                    },
                    "to": {
                        "source_package_name": to_source_package_name,
                        "source_package_version": to_source_package_version,
                        "version": to_deb_packages[package],
                    },
                    "notes": [
                        "For a newly added package only the three most recent changelog entries are shown."
                    ],
                    "cves": [],
                    "changes": [],
                }
                click.echo()
                if highlight_cves and cves_referenced:
                    click.echo("CVEs referenced in changelog:")
                    for cve_referenced in cves_referenced:
                        cve_priority_color = None
                        cve_priority_bold = False
                        if (
                            cve_referenced["cve_priority"] == "high"
                            or cve_referenced["cve_priority"] == "critical"
                        ):
                            cve_priority_color = "red"
                            cve_priority_bold = True
                        elif cve_referenced["cve_priority"] == "medium":
                            cve_priority_color = "yellow"
                            cve_priority_bold = True
                        click.echo(
                            "\t- {} ({} priority){}".format(
                                cve_referenced["cve"],
                                click.style(
                                    cve_referenced["cve_priority"],
                                    fg=cve_priority_color,
                                    bold=cve_priority_bold,
                                ),
                                ": {}".format(cve_referenced["cve_description"]),
                            )
                        )
                        changelog["added"]["deb"][package]["cves"].append(
                            cve_referenced
                        )
                    click.echo()
                for version_diff_changelogs_entry in version_diff_changelogs:
                    changelog["added"]["deb"][package]["changes"].append(
                        version_diff_changelogs_entry
                    )
                click.echo(version_diff_changelog)

            for package, from_to in deb_package_diffs.items():

                (
                    from_source_package_name,
                    from_source_package_version,
                ) = lib.get_source_package_details(
                    ubuntu,
                    launchpad,
                    from_lp_arch_series,
                    package,
                    from_to["from"],
                    ppas,
                )
                (
                    to_source_package_name,
                    to_source_package_version,
                ) = lib.get_source_package_details(
                    ubuntu, launchpad, to_lp_arch_series, package, from_to["to"], ppas
                )

                package_changelog_file = lib.get_changelog(
                    launchpad,
                    ubuntu,
                    to_lp_series,
                    tmp_cache_directory,
                    to_source_package_name,
                    to_source_package_version,
                    ppas,
                )

                # get changelog just between the from and to version
                (
                    version_diff_changelog,
                    cves_referenced,
                    version_diff_changelogs,
                ) = lib.parse_changelog(
                    launchpad,
                    package_changelog_file,
                    from_version=from_source_package_version,
                    to_version=to_source_package_version,
                    count=None,
                    highlight_cves=highlight_cves,
                )

                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} changed from version '{}' to version '{}' (source package changed from {} version '{}' to {} version '{}')".format(
                        package,
                        from_to["from"],
                        from_to["to"],
                        from_source_package_name,
                        from_source_package_version,
                        to_source_package_name,
                        to_source_package_version,
                    )
                )
                changelog["diff"]["deb"][package] = {
                    "from": {
                        "source_package_name": from_source_package_name,
                        "source_package_version": from_source_package_version,
                        "version": from_to["from"],
                    },
                    "to": {
                        "source_package_name": to_source_package_name,
                        "source_package_version": to_source_package_version,
                        "version": from_to["to"],
                    },
                    "cves": [],
                    "changes": [],
                }
                click.echo()
                if highlight_cves and cves_referenced:
                    click.echo("CVEs referenced in changelog:")
                    for cve_referenced in cves_referenced:
                        cve_priority_color = None
                        cve_priority_bold = False
                        if (
                            cve_referenced["cve_priority"] == "high"
                            or cve_referenced["cve_priority"] == "critical"
                        ):
                            cve_priority_color = "red"
                            cve_priority_bold = True
                        elif cve_referenced["cve_priority"] == "medium":
                            cve_priority_color = "yellow"
                            cve_priority_bold = True
                        click.echo(
                            "\t- {} ({} priority){}".format(
                                cve_referenced["cve"],
                                click.style(
                                    cve_referenced["cve_priority"],
                                    fg=cve_priority_color,
                                    bold=cve_priority_bold,
                                ),
                                ": {}".format(cve_referenced["cve_description"]),
                            )
                        )
                        changelog["diff"]["deb"][package]["cves"].append(cve_referenced)
                    click.echo()
                for version_diff_changelogs_entry in version_diff_changelogs:
                    changelog["diff"]["deb"][package]["changes"].append(
                        version_diff_changelogs_entry
                    )
                click.echo(version_diff_changelog)
    if output_json:
        with open(output_json, "w") as ouput_json_file:
            if output_json_pretty:
                json.dump(changelog, ouput_json_file, indent=4)
            else:
                json.dump(changelog, ouput_json_file)


if __name__ == "__main__":
    sys.exit(main())
