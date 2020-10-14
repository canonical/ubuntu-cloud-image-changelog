"""Main module."""
import os
import logging
import requests
import subprocess


def parse_changelog(changelog_filename, from_version, to_version):
    """
    Sends message to desktop using notify-send.
    """
    try:
        cmdline = ["dpkg-parsechangelog"]
        cmdline.extend(["-l", changelog_filename])
        cmdline.extend(["--from", from_version])
        cmdline.extend(["--to", to_version])

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


def get_changelog(cache_directory, package_name, package_version):
    """
    Download changelog for source / version and returns path to that

    :param str package_name: Source package name
    :param str package_version: Source package version
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
        "%s/%s/%s/changelog" % (package_prefix, package_name, package_version)
    )

    changelog = requests.get(changelog_url)
    valid_changelog = False
    with open(cache_filename, "wb") as cache_file:
        if changelog.status_code == 200:
            cache_file.write(changelog.content)
            valid_changelog = True
        else:
            cache_file.write(
                "Unable to find changelog for {} version {}. "
                "Was this package installed from a PPA "
                "perhaps?".format(package_name, package_version).encode("utf-8")
            )
            valid_changelog = False
            logging.error("missing %s: %s", package_name, changelog_url)

    return cache_filename, valid_changelog
