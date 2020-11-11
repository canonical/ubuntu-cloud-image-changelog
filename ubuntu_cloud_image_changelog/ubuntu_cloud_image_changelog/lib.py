"""Main module."""
import os
import logging
import requests
import subprocess
from debian import deb822
from debian.changelog import Changelog
from debian.debian_support import Version


def parse_ppa_changes(ppa_changes_filename):
    """
    parse ppa changes file
    """
    changelog = ""
    with open(ppa_changes_filename, "rb") as unparsed_ppa_changes_file:
        ppa_changes = unparsed_ppa_changes_file.read()
        change = deb822.Changes(ppa_changes)
        try:
            changelog += "{} version {} found in PPA \n\n".format(
                change.get_as_string("Source"), change.get_as_string("Version")
            )
            changelog += "Source: {}\n".format(change.get_as_string("Source"))
            changelog += "Version: {}\n".format(change.get_as_string("Version"))
            changelog += "Distribution: {}\n".format(
                change.get_as_string("Distribution")
            )
            changelog += "Urgency: {}\n".format(change.get_as_string("Urgency"))
            changelog += "Maintainer: {}\n".format(change.get_as_string("Maintainer"))
            changelog += "Changed-By: {}\n".format(change.get_as_string("Changed-By"))
            changelog += "Date: {}\n".format(change.get_as_string("Date"))
            changelog += "Changes:{}\n".format(change.get_as_string("Changes"))
        except:
            raise Exception(
                "Unable to parse PPA changes file {}".format(ppa_changes_filename)
            )
    return changelog


def parse_changelog(changelog_filename, from_version=None, to_version=None, count=1):
    """
    Extract changelog entries within a version range

    The range of changelog entries returned will include all entries
    after version_low up to, and including, version_high.
    If either the starting or ending version are not found in the
    list of changelog entries the result will be incomplete and
    a non-empty error message is returned to indicate the issue.
    """
    changelog = ""
    # Set max_blocks to none if we know the versions we want changelog for
    from_versions = []
    to_versions = []
    if from_version and to_version:
        # package versions in a changelog may or may not include the epoch
        from_versions.append(from_version)
        from_version_obj = Version(from_version)
        if from_version_obj.epoch:
            from_version_without_epoch = from_version_obj.full_version.replace(
                "{}:".format(from_version_obj.epoch), ""
            )
            from_versions.append(from_version_without_epoch)
        to_versions.append(to_version)
        to_version_obj = Version(to_version)
        if to_version_obj.epoch:
            to_version_without_epoch = to_version_obj.full_version.replace(
                "{}:".format(to_version_obj.epoch), ""
            )
            to_versions.append(to_version_without_epoch)
        # shim-signed is a special package as it appends the version of the
        # binary shim from Microsoft. This full version will not appear in
        # the manifest so we can safely remove anything after the binary
        # shim version.
        if "+" in from_version:
            from_versions.append(from_version[0 : from_version.index("+")])
        if "+" in to_version:
            to_versions.append(to_version[0 : to_version.index("+")])
        count = None

    with open(changelog_filename, "r") as fileptr:
        parsed_changelog = Changelog(fileptr.read(), max_blocks=count)
        start = False
        end = False
        try:
            changelog += "Source: {}\n".format(parsed_changelog.get_package())
            changelog += "Version: {}\n".format(parsed_changelog.version)
            changelog += "Distribution: {}\n".format(parsed_changelog.distributions)
            changelog += "Urgency: {}\n".format(parsed_changelog.urgency)
            changelog += "Maintainer: {}\n".format(parsed_changelog.author)
            changelog += "Date: {}\n".format(parsed_changelog.date)

            # The changelog blocks are in reverse order; we'll see high|to before low|from.
            change_blocks = []
            launchpad_bugs_fixed = []
            for changelog_block in parsed_changelog:
                if changelog_block.version in to_versions:
                    start = True
                    change_blocks = []
                if changelog_block.version in from_versions:
                    end = True
                    break
                launchpad_bugs_fixed += changelog_block.lp_bugs_closed
                changeblock_summary = "{} ({}) {}; urgency={}".format(
                    changelog_block.package,
                    changelog_block.version,
                    changelog_block.distributions,
                    changelog_block.urgency,
                )
                change_blocks.append((changeblock_summary, changelog_block))

            changelog += "Launchpad-Bugs-Fixed: {}\n".format(launchpad_bugs_fixed)
            changelog += "Changes:\n"
            for changeblock_summary, change_block in change_blocks:
                changelog += "{}\n".format(changeblock_summary)
                for change in change_block.changes():
                    changelog += "{}\n".format(change)
            # log a warning if we have no changelog or
            # from_version  ot found or to_version not found
            if (
                (from_version and not start)
                or (to_version and not end)
                or not changelog
            ):
                logging.warning(
                    "Unable to parse changelog {} for versions {} to {}".format(
                        changelog_filename, from_version, to_version
                    )
                )
        except Exception as ex:
            raise ex
            raise Exception(
                "Unable to parse package changelog {}".format(changelog_filename)
            )

        return changelog


def get_changelog(cache_directory, package_name, package_version, ppas):
    """
    Download changelog for source / version and returns path to that

    :param str package_name: Source package name
    :param str package_version: Source package version
    :param list ppas: List of possible ppas package installed from
    :raises Exception: If changelog file could not be downloaded
    :return: changelog file for source package & version
    :rtype: str
    """
    cache_filename = "%s/changelog.%s_%s" % (
        cache_directory,
        package_name,
        package_version,
    )

    if os.path.isfile(cache_filename):
        logging.debug("Using cached changelog for %s:%s", package_name, package_version)
        return cache_filename

    package_prefix = package_name[0:1]
    # packages starting with 'lib' are special
    if package_name.startswith("lib"):
        package_prefix = package_name[0:4]

    # packages ending with ':amd64' are special
    if package_name.endswith(":amd64"):
        package_name = package_name[:-6]

    # Changelog URL example http://changelogs.ubuntu.com/changelogs/ \
    #                           binary/s/sntp/1:4.2.8p12+dfsg-3ubuntu1/
    changelog_url = (
        "http://changelogs.ubuntu.com/changelogs/binary/"
        "{}/{}/{}/changelog".format(package_prefix, package_name, package_version)
    )

    changelog = requests.get(changelog_url)
    valid_changelog = False
    valid_ppa_changes = False
    with open(cache_filename, "wb") as cache_file:
        if changelog.status_code == 200:
            cache_file.write(changelog.content)
            valid_changelog = True
        else:
            valid_changelog = False
            # loop through all the specified PPAs and see if a changleog file
            for ppa in ppas:
                # Sample changes file URL from a PPA
                # https://launchpad.net/~cloud-images/+archive/ubuntu/docker1903-k8s/+files/containerd_1.2.10-0ubuntu1~18.04.0.2_source.changes
                ppa_changes_url = "{}/+files/{}_{}_source.changes".format(
                    ppa, package_name, package_version
                )
                ppa_changes = requests.get(ppa_changes_url)
                if ppa_changes.status_code == 200:
                    cache_file.write(ppa_changes.content)
                    valid_ppa_changes = True
                    break

        if not valid_ppa_changes and not valid_changelog:
            # can be found for this package and package version
            cache_file.write(
                "Unable to find changelog or ppa changes file for {} "
                "version {}.".format(package_name, package_version).encode("utf-8")
            )

    return cache_filename, valid_changelog, valid_ppa_changes
