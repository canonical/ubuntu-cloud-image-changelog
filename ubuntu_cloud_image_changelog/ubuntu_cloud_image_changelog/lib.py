"""Main module."""
import os
import logging
import urllib.parse
from debian.changelog import Changelog
from debian.debian_support import Version


def arch_independent_package_name(package_name):
    # packages ending with ':amd64' or ':arm64' are special
    if package_name.endswith(":amd64") or package_name.endswith(":arm64"):
        package_name = package_name[:-6]
    return package_name


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

        # An Ubuntu version might have ~ suffix. Remove this as it might not
        # always appear in the changelog
        if "~" in from_version:
            from_versions.append(from_version[0 : from_version.index("~")])
        if "~" in to_version:
            to_versions.append(to_version[0 : to_version.index("~")])

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
                changelog_block_versions = []
                changelog_block_versions.append(changelog_block.version.full_version)
                if "~" in changelog_block.version.full_version:
                    changelog_block_versions.append(changelog_block.version.full_version[0: changelog_block.version.full_version.index("~")])
                if "+" in changelog_block.version.full_version:
                    changelog_block_versions.append(changelog_block.version.full_version[0: changelog_block.version.full_version.index("+")])
                if changelog_block.version.epoch:
                    changelog_block_version_without_epoch = changelog_block.version.full_version.replace(
                        "{}:".format(changelog_block.version.epoch), ""
                    )
                    changelog_block_versions.append(changelog_block_version_without_epoch)
                for to_version in to_versions:
                    if to_version in changelog_block_versions:
                        start = True
                        break
                for from_version in from_versions:
                    if from_version in changelog_block_versions:
                        end = True
                        break
                if (not from_versions and not to_versions) or (start and not end):
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


def get_changelog(
    launchpad,
    ubuntu,
    lp_series,
    lp_arch_series,
    cache_directory,
    binary_package_name,
    package_version,
    ppas,
):
    """
    Download changelog for source / version and returns path to that
    :param launchpad: launchpad
    :param ubuntu: ubuntu
    :param lp_series: lp_series
    :param lp_arch_series: lp_arch_series
    :param str binary_package_name: Binary package name
    :param str package_version: Package version
    :param list ppas: List of possible ppas package installed from
    :raises Exception: If changelog file could not be downloaded
    :return: changelog file for source package & version
    :param str image_architecture: Architecture of the image which the manifest belongs to
    :rtype: str
    """
    # If there is an epoch in the installed binary package version then it
    # will not appear in the source versions in the changelog.
    # As such we can remove before downloading the changelogs.
    package_version_obj = Version(package_version)
    if package_version_obj.epoch:
        package_version_without_epoch = package_version_obj.full_version.replace(
            "{}:".format(package_version_obj.epoch), ""
        )
        package_version = package_version_without_epoch
    # packages ending with ':amd64' or ':arm64' are special
    binary_package_name = arch_independent_package_name(binary_package_name)

    cache_filename = "%s/changelog.%s_%s" % (
        cache_directory,
        binary_package_name,
        package_version,
    )

    if os.path.isfile(cache_filename):
        logging.debug(
            "Using cached changelog for %s:%s", binary_package_name, package_version
        )
        return cache_filename

    package_version_in_archive_changelog = False
    package_version_in_ppa_changelog = False
    with open(cache_filename, "wb") as cache_file:
        archive = ubuntu.main_archive
        binaries = archive.getPublishedBinaries(
            exact_match=True,
            binary_name=binary_package_name,
            distro_arch_series=lp_arch_series,
            status="Published",
            order_by_date=True,
        )
        if len(binaries):
            # now get the source package name so we can get the changelog
            source_package_name = binaries[0].source_package_name
            sources = archive.getPublishedSources(
                exact_match=True,
                source_name=source_package_name,
                distro_series=lp_series,
                status="Published",
                order_by_date=True,
            )
            if len(sources):
                archive_changelog_url = sources[0].changelogUrl()

                _patched_archive_changelog_url = launchpad._root_uri.append(
                    urllib.parse.urlparse(archive_changelog_url).path.lstrip("/")
                )

                archive_changelog = launchpad._browser.get(
                    _patched_archive_changelog_url
                )

                if package_version in archive_changelog.decode("utf-8"):
                    cache_file.write(archive_changelog)
                    package_version_in_archive_changelog = True

        if not package_version_in_archive_changelog:
            # Attempt to get the changelog from any of the passed in PPAs instead
            for ppa in ppas:
                ppa_owner, ppa_name = ppa.split("/")
                archive = launchpad.people[ppa_owner].getPPAByName(name=ppa_name)
                # using pocket "Release" when using a PPA ...'
                pocket = "Release"
                binaries = archive.getPublishedBinaries(
                    exact_match=True,
                    binary_name=binary_package_name,
                    distro_arch_series=lp_arch_series,
                    status="Published",
                    pocket=pocket,
                    order_by_date=True,
                )
                if len(binaries):
                    # now get the source package name so we can get the changelog
                    source_package_name = binaries[0].source_package_name
                    sources = archive.getPublishedSources(
                        exact_match=True,
                        pocket=pocket,
                        source_name=source_package_name,
                        distro_series=lp_series,
                        status="Published",
                        order_by_date=True,
                    )
                    if len(sources) == 1:
                        ppa_changelog_url = sources[0].changelogUrl()

                        _patched_ppa_changelog_url = launchpad._root_uri.append(
                            urllib.parse.urlparse(ppa_changelog_url).path.lstrip("/")
                        )

                        ppa_changelog = launchpad._browser.get(
                            _patched_ppa_changelog_url
                        )

                        if package_version in ppa_changelog.decode("utf-8"):
                            cache_file.write(ppa_changelog)
                            package_version_in_ppa_changelog = True
                            break  # no need to continue iterating the PPA list

        if (
            not package_version_in_archive_changelog
            and not package_version_in_ppa_changelog
        ):
            # can be found for this package and package version
            cache_file.write(
                "Unable to find changelog for {} "
                "version {}.".format(binary_package_name, package_version).encode(
                    "utf-8"
                )
            )

    return cache_filename
