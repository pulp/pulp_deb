=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.
    To add a new change log entry, please see
    https://docs.pulpproject.org/en/3.0/nightly/contributing/git.html#changelog-update

    WARNING: Don't drop the next directive!

.. towncrier release notes start

2.0.0b2 (2019-10-02)
====================

Features
--------


- Rework Package and InstallerPackage serializers to allow creation from artifact or uploaded file with specifying any metadata.
  `#5379 <https://pulp.plan.io/issues/5379>`_
- Change generic content serializer to create content units by either specifying an artifact or uploading a file.
  `#5403 <https://pulp.plan.io/issues/5403>`_,
  `#5487 <https://pulp.plan.io/issues/5487>`_



Deprecations and Removals
-------------------------


- Remove one shot uploader in favor of the combined create endpoint.
  `#5403 <https://pulp.plan.io/issues/5403>`_



Bugfixes
--------


- Change content serializers to use relative_path instead of _relative_path.
  `#5376 <https://pulp.plan.io/issues/5376>`_



Improved Documentation
----------------------


- Change the prefix of Pulp services from pulp-* to pulpcore-*
  `#4554 <https://pulp.plan.io/issues/4554>`_
- Reflect artifact and upload functionality in the content create endpoint documentation.
  `#5371 <https://pulp.plan.io/issues/5371>`_



Misc
----


- PublishedMetadata is now a type of Content.
  `#5304 <https://pulp.plan.io/issues/5304>`_
- Replace `ProgressBar` with `ProgressReport`.
  `#5477 <https://pulp.plan.io/issues/5477>`_



----


2.0.0b1 (2019-09-06)
====================

Features
--------


- Add oneshot upload functionality for deb type packages.
  `#5391 <https://pulp.plan.io/issues/5391>`_



Bugfixes
--------


- Add relative_path to package units natural key to fix uniqueness constraints.
  `#5377 <https://pulp.plan.io/issues/5377>`_
- Fix publishing of lazy content and add download_policy tests.
  `#5405 <https://pulp.plan.io/issues/5405>`_



Improved Documentation
----------------------


- Reference the fact you must have both _relative_path and relative_path.
  `#5376 <https://pulp.plan.io/issues/5376>`_
- Fix various documentation issues from API changes, plus other misc fixes.
  `#5380 <https://pulp.plan.io/issues/5380>`_



Misc
----


- Adopting related names on models.
  `#4681 <https://pulp.plan.io/issues/4681>`_
- Generate and commit initial migrations.
  `#5401 <https://pulp.plan.io/issues/5401>`_





