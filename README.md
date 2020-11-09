# ubuntu-cloud-image-changelog
Helpful utility to generate package changelog between two cloud images

Install
-------

Install from snap store

This release is also available for download and install from the snap store @ https://snapcraft.io/ubuntu-cloud-image-changelog

```
sudo snap install ubuntu-cloud-image-changelog
```

This is a strict snap as recommended for most snaps, see https://snapcraft.io/docs/snap-confinement for more details.


Install from PyPi

```
pip install ubuntu-cloud-image-changelog
```

Usage
-----

```
ubuntu-cloud-image-changelog --from-manifest manifest1.manifest --to-manifest manifest2.manifest
```

If Packages in manifest are known to have been installed from this PPA then you can pass one of more PPAs to ubuntu-cloud-image-changelog for the changelog for those packages to be included in the output.

```
--ppa
```

Expected format is 'https://launchpad.net/~%LAUNCHPAD_USERNAME%/+archive/ubuntu/%PPA_NAME%'
