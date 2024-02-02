#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["Click>=7.0", "colorama", "launchpadlib", "pydantic>=2", "python-debian"]

setup(
    author="Philip Roche",
    author_email="phil.roche@canonical.com",
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Helpful utility to generate package changelog between two cloud images",
    entry_points={
        "console_scripts": [
            "ubuntu-cloud-image-changelog=ubuntu_cloud_image_changelog.cli:cli",
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="ubuntu_cloud_image_changelog",
    name="ubuntu-cloud-image-changelog",
    packages=find_packages(include=["ubuntu_cloud_image_changelog", "ubuntu_cloud_image_changelog.*"]),
    url="https://github.com/CanonicalLtd/ubuntu-cloud-image-changelog",
    version="0.15.1",
    zip_safe=False,
)
