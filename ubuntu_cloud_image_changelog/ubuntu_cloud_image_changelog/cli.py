"""Console script for ubuntu_cloud_image_changelog."""
import os
import json
import tempfile
from typing import List, Optional

import click

from ubuntu_cloud_image_changelog import launchpadagent, lib
from ubuntu_cloud_image_changelog.models import (
    Added,
    ChangelogModel,
    DebPackage,
    DebSummary,
    Diff,
    FromVersion,
    Removed,
    SnapPackage,
    SnapSummary,
    Summary,
    ToVersion,
)


@click.group()
@click.pass_context
def cli(ctx):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--lp-credentials-store",
    envvar="LP_CREDENTIALS_STORE",
    required=False,
    help="An optional path to an already configured launchpad credentials store.",
    default=None,
)
@click.option("--from-series", help='the Ubuntu series eg. "20.04" or "focal"', required=True)
@click.option("--to-series", help='the Ubuntu series eg. "20.04" or "focal"', required=True)
@click.option(
    "--from-serial", help="The Ubuntu cloud image serial (cat /etc/cloud/build.info)", required=False, default=None
)
@click.option(
    "--to-serial", help="The Ubuntu cloud image serial (cat /etc/cloud/build.info)", required=False, default=None
)
@click.option(
    "--from-manifest",
    required=True,
    type=click.File("rb"),
    help="From manifest."
    "{}".format(
        "When using the ubuntu-cloud-image-changelog " "snap this config must reside under $HOME."
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
        "When using the ubuntu-cloud-image-changelog " "snap this config must reside under $HOME."
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
    help="Highlight the CVEs referenced in each individual changelog entry" ". Default: %(default)s",
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
@click.option(
    "--notes",
    help="Free form text to include in the changelog. ",
    default=None,
    show_default=True,
)
@click.pass_context
def generate(
    ctx,
    lp_credentials_store: Optional[str],
    from_series: str,
    to_series: str,
    from_serial: str,
    to_serial: str,
    from_manifest: click.File,
    to_manifest: click.File,
    ppas: List[str],
    image_architecture: str,
    highlight_cves: bool,
    output_json: Optional[str],
    output_json_pretty: bool,
    notes: Optional[str],
):
    from_manifest_lines = from_manifest.readlines()
    to_manifest_lines = to_manifest.readlines()
    from_deb_packages = {}
    to_deb_packages = {}
    from_snap_packages = {}
    to_snap_packages = {}
    snap_package_prefix = "snap:"

    removed_deb_packages = []

    deb_package_added = {}

    deb_package_diffs = {}

    removed_snap_packages = []

    snap_package_added = {}

    snap_package_diffs = {}
    with tempfile.TemporaryDirectory(prefix="ubuntu-cloud-image-changelog") as tmp_cache_directory:
        launchpad = launchpadagent.get_launchpad(
            launchpadlib_dir=tmp_cache_directory,
            lp_credentials_store=lp_credentials_store,
        )
        ubuntu = launchpad.distributions["ubuntu"]
        to_lp_series = ubuntu.getSeries(name_or_version=to_series)
        from_lp_series = ubuntu.getSeries(name_or_version=from_series)
        to_lp_arch_series = to_lp_series.getDistroArchSeries(archtag=image_architecture)
        from_lp_arch_series = from_lp_series.getDistroArchSeries(archtag=image_architecture)

        # Store all changelog items in a ChangelogModel object so we can output in different formats and not just txt.
        changelog = ChangelogModel(
            notes=notes,
            from_series=from_series,
            to_series=to_series,
            from_serial=from_serial,
            to_serial=to_serial,
            from_manifest_filename=from_manifest.name,
            to_manifest_filename=to_manifest.name,
            summary=Summary(
                snap=SnapSummary(added=[], removed=[], diff=[]),
                deb=DebSummary(added=[], removed=[], diff=[]),
            ),
            diff=Diff(deb=[], snap=[]),
            added=Added(deb=[], snap=[]),
            removed=Removed(deb=[], snap=[]),
        )

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
                    removed_snap_package = SnapPackage(
                        name=package,
                        from_version=FromVersion(version=version),
                        to_version=ToVersion(version=None),
                    )
                    changelog.removed.snap.append(removed_snap_package)

            for package, version in to_snap_packages.items():
                if package not in from_snap_packages.keys():
                    snap_package_added[package] = {
                        "from": None,
                        "to": version,
                    }

            for to_package, to_package_version in to_snap_packages.items():
                # only need to find diff for packages that are not new
                if to_package not in snap_package_added.keys():
                    from_package_version = from_snap_packages[to_package]
                    if from_package_version != to_package_version:
                        snap_package_diffs[to_package] = {
                            "from": from_package_version,
                            "to": to_package_version,
                        }

            changelog.summary.snap = SnapSummary(
                added=list(snap_package_added.keys()),
                removed=removed_snap_packages,
                diff=list(snap_package_diffs.keys()),
            )

            click.echo("Snap packages added: {}".format(list(snap_package_added.keys())))
            click.echo("Snap packages removed: {}".format(removed_snap_packages))
            click.echo("Snap packages changed: {}".format(list(snap_package_diffs.keys())))

        # Are there any deb package diffs?
        if from_deb_packages or to_deb_packages:
            for package, version in from_deb_packages.items():
                if package not in to_deb_packages.keys():
                    removed_deb_packages.append(package)
                    # Get the source package name and source package version for the removed package
                    (
                        removed_source_package_name,
                        removed_source_package_version,
                    ) = lib.get_source_package_details(
                        ubuntu,
                        launchpad,
                        to_lp_arch_series,
                        package,
                        version,
                        ppas,
                    )

                    removed_deb_package = DebPackage(
                        name=package,
                        from_version=FromVersion(
                            version=version,
                            source_package_name=removed_source_package_name,
                            source_package_version=removed_source_package_version,
                        ),
                        to_version=ToVersion(version=None),
                    )

                    changelog.removed.deb.append(removed_deb_package)

            for to_package, to_package_version in to_deb_packages.items():
                if to_package not in from_deb_packages.keys():
                    # add the summary of version changes for this package fo easier parsing later
                    deb_package_added[to_package] = {
                        "from": None,
                        "to": to_package_version,
                    }

            for to_package, to_package_version in to_deb_packages.items():
                # only need to find diff for packages that are not new
                if to_package not in deb_package_added.keys():
                    from_package_version = from_deb_packages[to_package]
                    if from_package_version != to_package_version:
                        # add the summary of version changes for this package fo easier parsing later
                        deb_package_diffs[to_package] = {
                            "from": from_package_version,
                            "to": to_package_version,
                        }

            changelog.summary.deb = DebSummary(
                added=list(deb_package_added.keys()),
                removed=removed_deb_packages,
                diff=list(deb_package_diffs.keys()),
            )
            click.echo("Deb packages added: {}".format(list(deb_package_added.keys())))
            click.echo("Deb packages removed: {}".format(removed_deb_packages))
            click.echo("Deb packages changed: {}".format(list(deb_package_diffs.keys())))

        if snap_package_diffs or snap_package_added:
            click.echo(
                "\n** Package version diffs for for changed snap packages "
                "below. Full changelog for snap packages are not listed **\n"
            )

            # for each of the snap package diffs list the diff in versions
            for package, from_to in snap_package_added.items():
                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} version '{}' was added.".format(
                        package,
                        from_to["to"],
                    )
                )

                added_snap_package_to_version = ToVersion(version=from_to["to"])
                added_snap_package_from_version = FromVersion(version=from_to["from"])
                added_snap_package = SnapPackage(
                    name=package,
                    from_version=added_snap_package_from_version,
                    to_version=added_snap_package_to_version,
                )

                changelog.added.snap.append(added_snap_package)
                click.echo()

            # for each of the snap package diffs list the diff in versions
            for package, from_to in snap_package_diffs.items():
                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} changed from version '{}' to version '{}'".format(package, from_to["from"], from_to["to"])
                )

                diff_snap_package_to_version = ToVersion(version=from_to["to"])
                diff_snap_package_from_version = FromVersion(version=from_to["from"])
                diff_snap_package = SnapPackage(
                    name=package,
                    from_version=diff_snap_package_from_version,
                    to_version=diff_snap_package_to_version,
                )

                changelog.diff.snap.append(diff_snap_package)
                click.echo()

        if deb_package_diffs or deb_package_added:
            click.echo("\n** Changelogs for added and changed deb packages " "below: **\n")

            # for each of the deb package diffs and new packages download the
            # changelog
            for package, from_to in deb_package_added.items():
                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                (
                    to_source_package_name,
                    to_source_package_version,
                ) = lib.get_source_package_details(
                    ubuntu,
                    launchpad,
                    to_lp_arch_series,
                    package,
                    from_to["to"],
                    ppas,
                )
                to_package_changelog_file = lib.get_changelog(
                    launchpad,
                    ubuntu,
                    to_lp_series,
                    tmp_cache_directory,
                    to_source_package_name,
                    to_source_package_version,
                    ppas,
                )

                # Is the source package of this added binary package the same as the source package of a removed
                # binary package? If so then this is likley a binary package rename and we can get the changelog between
                # the source package version removed and the source package version added.
                notes = None
                version_added_changelogs = []
                for removed_deb_package in changelog.removed.deb:
                    if removed_deb_package.from_version.source_package_name == to_source_package_name:
                        removed_source_package_name = removed_deb_package.from_version.source_package_name
                        removed_source_package_version = removed_deb_package.from_version.source_package_version
                        removed_source_package_changelog_file = lib.get_changelog(
                            launchpad,
                            ubuntu,
                            from_lp_series,
                            tmp_cache_directory,
                            removed_source_package_name,
                            removed_source_package_version,
                            ppas,
                        )
                        version_added_changelogs = lib.parse_changelog(
                            launchpad,
                            to_changelog_filename=to_package_changelog_file,
                            to_version=to_source_package_version,
                            from_changelog_filename=removed_source_package_changelog_file,
                            count=None,
                            highlight_cves=highlight_cves,
                        )
                        added_deb_package_from_version = FromVersion(
                            version=None,
                            source_package_name=removed_source_package_name,
                            source_package_version=removed_source_package_version,
                        )
                        notes = (
                            "{} version '{}' (source package {} version '{}') was added. "
                            "{} version '{}' has the same source package name, "
                            "{}, as removed package {}. As such we can use the source package version of the "
                            "removed package, '{}', as the starting point in our changelog diff. Kernel packages "
                            "are an example of where the binary package name changes for the same source "
                            "package. Using the removed package source package version as our starting point "
                            "means we can still get meaningful changelog diffs even for what appears to be "
                            "a new package.".format(
                                package,
                                from_to["to"],
                                to_source_package_name,
                                to_source_package_version,
                                package,
                                from_to["to"],
                                to_source_package_name,
                                removed_deb_package.name,
                                removed_deb_package.from_version.source_package_version,
                            )
                        )
                        click.echo(notes)
                        break

                # If the source package of this added binary package is not the same as the source package of a removed
                # binary package then get the three most recent changelog entries
                if not version_added_changelogs:
                    version_added_changelogs = lib.parse_changelog(
                        launchpad,
                        to_changelog_filename=to_package_changelog_file,
                        to_version=to_source_package_version,
                        count=3,
                        highlight_cves=highlight_cves,
                    )
                    added_deb_package_from_version = FromVersion(version=None)
                    notes = "For a newly added package only the three most recent changelog entries are shown."
                    click.echo(
                        "{} version '{}' (source package {} version '{}') was added. "
                        "Below are the three most recent changelog entries".format(
                            package,
                            from_to["to"],
                            to_source_package_name,
                            to_source_package_version,
                        )
                    )
                click.echo()

                added_deb_package_to_version = ToVersion(
                    version=from_to["to"],
                    source_package_name=to_source_package_name,
                    source_package_version=to_source_package_version,
                )
                added_deb_package = DebPackage(
                    name=package,
                    from_version=added_deb_package_from_version,
                    to_version=added_deb_package_to_version,
                    notes=notes,
                )

                for version_added_changelog_change in version_added_changelogs:
                    added_deb_package.cves.extend(version_added_changelog_change.cves)
                    added_deb_package.launchpad_bugs_fixed.extend(version_added_changelog_change.launchpad_bugs_fixed)
                    added_deb_package.changes.append(version_added_changelog_change)

                click.echo("Source: {}".format(to_source_package_name))
                click.echo("Version: {}".format(to_source_package_version))
                click.echo("Distribution: {}".format(added_deb_package.changes[0].distributions))
                click.echo("Urgency: {}".format(added_deb_package.changes[0].urgency))
                click.echo("Maintainer: {}".format(added_deb_package.changes[0].author))
                click.echo("Date: {}".format(added_deb_package.changes[0].date))
                click.echo(
                    "Launchpad-Bugs-Fixed: {}".format(
                        ", ".join(
                            [str(launchpad_bug_fixed) for launchpad_bug_fixed in added_deb_package.launchpad_bugs_fixed]
                        )
                    )
                )
                if highlight_cves and added_deb_package.cves:
                    click.echo(
                        "CVEs referenced: {}".format(
                            ", ".join([cve_referenced.cve for cve_referenced in added_deb_package.cves])
                        )
                    )

                for changelog_entry in added_deb_package.changes:
                    echo_changes(highlight_cves, changelog_entry)

                changelog.added.deb.append(added_deb_package)

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
                ) = lib.get_source_package_details(ubuntu, launchpad, to_lp_arch_series, package, from_to["to"], ppas)

                from_package_changelog_file = lib.get_changelog(
                    launchpad,
                    ubuntu,
                    from_lp_series,
                    tmp_cache_directory,
                    from_source_package_name,
                    from_source_package_version,
                    ppas,
                )

                to_package_changelog_file = lib.get_changelog(
                    launchpad,
                    ubuntu,
                    to_lp_series,
                    tmp_cache_directory,
                    to_source_package_name,
                    to_source_package_version,
                    ppas,
                )

                # get changelog just between the from and to version

                version_diff_changelogs = lib.parse_changelog(
                    launchpad,
                    to_changelog_filename=to_package_changelog_file,
                    to_version=to_source_package_version,
                    from_changelog_filename=from_package_changelog_file,
                    count=None,
                    highlight_cves=highlight_cves,
                )

                click.echo(
                    "==========================================================="
                    "==========================================================="
                )
                click.echo(
                    "{} changed from version '{}' to version '{}' "
                    "(source package changed from {} version '{}' to {} version '{}')".format(
                        package,
                        from_to["from"],
                        from_to["to"],
                        from_source_package_name,
                        from_source_package_version,
                        to_source_package_name,
                        to_source_package_version,
                    )
                )
                click.echo()

                diff_deb_package_to_version = ToVersion(
                    version=from_to["to"],
                    source_package_name=to_source_package_name,
                    source_package_version=to_source_package_version,
                )
                diff_deb_package_from_version = FromVersion(
                    version=from_to["from"],
                    source_package_name=from_source_package_name,
                    source_package_version=from_source_package_version,
                )
                diff_deb_package = DebPackage(
                    name=package,
                    from_version=diff_deb_package_from_version,
                    to_version=diff_deb_package_to_version,
                )

                for version_diff_changelog_change in version_diff_changelogs:
                    diff_deb_package.cves.extend(version_diff_changelog_change.cves)
                    diff_deb_package.launchpad_bugs_fixed.extend(version_diff_changelog_change.launchpad_bugs_fixed)
                    diff_deb_package.changes.append(version_diff_changelog_change)

                click.echo("Source: {}".format(to_source_package_name))
                click.echo("Version: {}".format(to_source_package_version))
                click.echo("Distribution: {}".format(diff_deb_package.changes[0].distributions))
                click.echo("Urgency: {}".format(diff_deb_package.changes[0].urgency))
                click.echo("Maintainer: {}".format(diff_deb_package.changes[0].author))
                click.echo("Date: {}".format(diff_deb_package.changes[0].date))
                click.echo(
                    "Launchpad-Bugs-Fixed: {}".format(
                        ",".join(
                            [str(launchpad_bug_fixed) for launchpad_bug_fixed in diff_deb_package.launchpad_bugs_fixed]
                        )
                    )
                )
                if highlight_cves and diff_deb_package.cves:
                    click.echo(
                        "CVEs referenced: {}".format(
                            ",".join([cve_referenced.cve for cve_referenced in diff_deb_package.cves])
                        )
                    )

                for changelog_entry in diff_deb_package.changes:
                    echo_changes(highlight_cves, changelog_entry)

                changelog.diff.deb.append(diff_deb_package)

    if output_json:
        with open(output_json, "w") as ouput_json_file:
            if output_json_pretty:
                ouput_json_file.write(changelog.model_dump_json(indent=4))
            else:
                ouput_json_file.write(changelog.model_dump_json())


def echo_changes(highlight_cves, version_changelog_change):
    changeblock_summary = "{} ({}) {}; urgency={}".format(
        version_changelog_change.package,
        version_changelog_change.version,
        version_changelog_change.distributions,
        version_changelog_change.urgency,
    )
    click.echo()
    click.echo("{}".format(changeblock_summary))
    click.echo("{} ({})".format(version_changelog_change.author, version_changelog_change.date))
    click.echo()
    if highlight_cves and version_changelog_change.cves:
        click.echo("CVEs referenced in changelog:")
        for cve_referenced in version_changelog_change.cves:
            cve_priority_color = None
            cve_priority_bold = False
            if cve_referenced.cve_priority == "high" or cve_referenced.cve_priority == "critical":
                cve_priority_color = "red"
                cve_priority_bold = True
            elif cve_referenced.cve_priority == "medium":
                cve_priority_color = "yellow"
                cve_priority_bold = True
            click.echo(
                "\t- {} ({} priority){}".format(
                    cve_referenced.cve,
                    click.style(
                        cve_referenced.cve_priority,
                        fg=cve_priority_color,
                        bold=cve_priority_bold,
                    ),
                    ": {}".format(cve_referenced.cve_description),
                )
            )
        click.echo()

    click.echo("Changes:")
    for log_entry in version_changelog_change.log:
        click.echo(log_entry)


@cli.command()
@click.pass_context
def schema(ctx):
    click.echo(json.dumps(ChangelogModel.model_json_schema(), indent=4))


if __name__ == "__main__":
    cli(obj={})
