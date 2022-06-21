"""Main module."""
import os
import logging
import urllib.parse
from debian.changelog import Changelog
from debian.debian_support import Version


def get_source_package_details(ubuntu, launchpad, lp_arch_series, binary_package_name, binary_package_version, ppas):
    # find the published binary for this series, binary_package_name
    # and binary_package_version
    source_package_name = None
    source_package_version = None
    archive = ubuntu.main_archive
    binaries = archive.getPublishedBinaries(
        exact_match=True,
        binary_name=binary_package_name,
        distro_arch_series=lp_arch_series,
        order_by_date=True,
        version=binary_package_version,
    )
    if len(binaries):
        # now get the source package name so we can get the changelog
        source_package_name = binaries[0].source_package_name
        source_package_version = binaries[0].source_package_version
    else:
        # search through the PPAs to see if this binary version was published
        # there.
        for ppa in ppas:
            ppa_owner, ppa_name = ppa.split("/")
            archive = launchpad.people[ppa_owner].getPPAByName(name=ppa_name)
            # using pocket "Release" when using a PPA ...'
            pocket = "Release"
            binaries = archive.getPublishedBinaries(
                exact_match=True,
                binary_name=binary_package_name,
                distro_arch_series=lp_arch_series,
                pocket=pocket,
                order_by_date=True,
                version=binary_package_version,
            )
            if len(binaries):
                # now get the source package name so we can get the changelog
                source_package_name = binaries[0].source_package_name
                source_package_version = binaries[0].source_package_version

    return source_package_name, source_package_version


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

    if not to_version:
        raise Exception("to_version must be specified when parsing changelog")

    with open(changelog_filename, "r") as fileptr:
        try:
            parsed_changelog = Changelog(fileptr.read())
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
                if changelog_block.version:
                    # if changelog_block.version is None then this is a
                    # changelog we are unable to parse
                    changelog_version_equal_to_or_before_to_version = Version(changelog_block.version.full_version) <= Version(to_version)

                    if from_version:
                        if Version(changelog_block.version.full_version) <= Version(from_version):
                            # If we have reached our from version then we can
                            # stop parsing
                            break

                    if changelog_version_equal_to_or_before_to_version:
                        launchpad_bugs_fixed += changelog_block.lp_bugs_closed
                        changeblock_summary = "{} ({}) {}; urgency={}".format(
                            changelog_block.package,
                            changelog_block.version,
                            changelog_block.distributions,
                            changelog_block.urgency,
                        )
                        change_blocks.append((changeblock_summary, changelog_block))
                    if count and len(change_blocks) == count:
                        break  # we have enough blocks now

            changelog += "Launchpad-Bugs-Fixed: {}\n".format(launchpad_bugs_fixed)
            changelog += "Changes:\n"
            for changeblock_summary, change_block in change_blocks:
                changelog += "{}\n".format(changeblock_summary)
                for change in change_block.changes():
                    changelog += "{}\n".format(change)
            # log a warning if we have no changelog or
            # from_version  ot found or to_version not found
            if not changelog:
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
    cache_directory,
    source_package_name,
    source_package_version,
    ppas,
):
    """
    Download changelog for source / version and returns path to that
    :param launchpad: launchpad
    :param ubuntu: ubuntu
    :param lp_series: lp_series
    :param str source_package_name: Binary package name
    :param str source_package_version: Package version
    :param list ppas: List of possible ppas package installed from
    :raises Exception: If changelog file could not be downloaded
    :return: changelog file for source package & version
    :param str image_architecture: Architecture of the image which the manifest belongs to
    :rtype: str
    """

    cache_filename = "%s/changelog.%s_%s" % (
        cache_directory,
        source_package_name,
        source_package_version,
    )

    if os.path.isfile(cache_filename):
        logging.debug(
            "Using cached changelog for %s:%s", source_package_name, source_package_version
        )
        return cache_filename

    package_version_in_archive_changelog = False
    package_version_in_ppa_changelog = False
    with open(cache_filename, "wb") as cache_file:
        archive = ubuntu.main_archive

        # Get the published sources for this exact version
        sources = archive.getPublishedSources(
            exact_match=True,
            source_name=source_package_name,
            distro_series=lp_series,
            order_by_date=True,
            version=source_package_version,
        )
        if len(sources):
            archive_changelog_url = sources[0].changelogUrl()

            _patched_archive_changelog_url = launchpad._root_uri.append(
                urllib.parse.urlparse(archive_changelog_url).path.lstrip("/")
            )

            archive_changelog = launchpad._browser.get(
                _patched_archive_changelog_url
            )

            if source_package_version in archive_changelog.decode("utf-8"):
                cache_file.write(archive_changelog)
                package_version_in_archive_changelog = True

        if not package_version_in_archive_changelog:
            # Attempt to get the changelog from any of the passed in PPAs instead
            for ppa in ppas:
                ppa_owner, ppa_name = ppa.split("/")
                archive = launchpad.people[ppa_owner].getPPAByName(name=ppa_name)
                # using pocket "Release" when using a PPA ...'
                pocket = "Release"
                sources = archive.getPublishedSources(
                    exact_match=True,
                    pocket=pocket,
                    source_name=source_package_name,
                    distro_series=lp_series,
                    order_by_date=True,
                    version=source_package_version
                )
                if len(sources):
                    ppa_changelog_url = sources[0].changelogUrl()

                    _patched_ppa_changelog_url = launchpad._root_uri.append(
                        urllib.parse.urlparse(ppa_changelog_url).path.lstrip("/")
                    )

                    ppa_changelog = launchpad._browser.get(
                        _patched_ppa_changelog_url
                    )

                    if source_package_version in ppa_changelog.decode("utf-8"):
                        cache_file.write(ppa_changelog)
                        package_version_in_ppa_changelog = True
                        break  # no need to continue iterating the PPA list

        if (
            not package_version_in_archive_changelog
            and not package_version_in_ppa_changelog
        ):
            # can be found for this package and package version
            cache_file.write(
                "Unable to find changelog for srouce package {} "
                "version {}.".format(source_package_name, source_package_version).encode(
                    "utf-8"
                )
            )

    return cache_filename
