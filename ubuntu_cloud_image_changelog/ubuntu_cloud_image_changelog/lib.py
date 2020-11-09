"""Main module."""
import os
import logging
import requests
import subprocess
from debian import deb822


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
    parse changelog using dpkg-parsechangelog
    """
    try:
        cmdline = ["dpkg-parsechangelog"]
        cmdline.extend(["-l", changelog_filename])
        if from_version and to_version:
            cmdline.extend(["--from", from_version])
            cmdline.extend(["--to", to_version])
        else:
            cmdline.extend(["--count", str(count)])

        process = subprocess.Popen(
            " ".join(cmdline),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        out, err = process.communicate()

        # Check the error state
        retcode = process.returncode
        if retcode:
            raise Exception(
                'Call failed for {} rc:{} "{}"'.format(cmdline, retcode, err)
            )
        return out

    except Exception as e:
        logging.error("Error sending dpkg-parsechangelog: %s", str(e))


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
