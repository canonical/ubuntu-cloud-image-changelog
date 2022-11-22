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
ubuntu-cloud-image-changelog --from-manifest manifest1.manifest --to-manifest manifest2.manifest --from-series focal --to-series focal
```

If Packages in manifest are known to have been installed from this PPA then you can pass one of more PPAs to ubuntu-cloud-image-changelog for the changelog for those packages to be included in the output.

```
--ppa
```

Expected format is '%LAUNCHPAD_USERNAME%/%PPA_NAME%' eg. philroche/cloud-init

```
--highlight-cves
```

Highlight the CVEs referenced in each individual changelog entry

```
--output-json changelog.json
```

Output changelog to local `changelog.json` file

```
--output-json-pretty
```

Pretty print JSON output with 4 character indentation.  `--output-json` must also be used for this to take affect.

TODO
----

* There are opportunities to improve performance by parallelizing the source package changelog queries and parsing.
* Refactor the generate function as it is way too long and complex.
* Add tests for the generate function.