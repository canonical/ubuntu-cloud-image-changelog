=======
History
=======

0.8.1 (2020-11-11)
------------------

* Improve handling of changelog parsing if from version or to version not found

0.8.0 (2020-11-09)
------------------

* handle package version that do not exactly conform to debian package version
  shim-signed is a special package as it appends the version of the
  binary shim from Microsoft. This full version will not appear in
  the manifest so we can safely remove anything after the binary shim version.

  Example version: 1.37~18.04.6+15+1533136590.3beb971-0ubuntu1


0.7.3 (2020-11-09)
------------------

* package versions in a changelog may or may not include the epoch

0.7.2 (2020-11-09)
------------------

* use consistent ubuntu-cloud-image-changelog entry point

0.7 (2020-11-09)
------------------

* Remove dependency on dpkg-parsechangelog utility.
  Use python-debian to parse changelogs instead

0.6 (2020-11-09)
------------------

* First release on PyPI.
