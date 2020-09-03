================================================================================
Changelog
================================================================================

..
   You should *NOT* be adding new change log entries to this file, this file is managed by towncrier.
   You *may* edit previous change logs to correct typos or similar.
   To learn how to add new entries see the 'Changelog Update' heading in the CONTRIBUTING.rst file.

   WARNING: Don't drop the next directive!

.. towncrier release notes start

2.6.1 (2020-09-03)
==================

Misc
----

- Dropped the beta status of the plugin. The plugin is now GA!
  `#6999 <https://pulp.plan.io/issues/6999>`_


----


2.6.0b1 (2020-09-01)
====================

Features
--------

- Added handling of packages with the same name, version, and architecture, when saving a new repository version.
  `#6429 <https://pulp.plan.io/issues/6429>`_
- Both simple and structured publish now use separate ``Architecture: all`` package indecies only.
  `#6991 <https://pulp.plan.io/issues/6991>`_


Bugfixes
--------

- Optional version strings are now stripped from the sourcename before using it for package file paths.
  `#7153 <https://pulp.plan.io/issues/7153>`_
- Fixed several field names in the to deb822 translation dict.
  `#7190 <https://pulp.plan.io/issues/7190>`_
- ``Section`` and ``Priority`` are no longer required for package indecies.
  `#7236 <https://pulp.plan.io/issues/7236>`_
- Fixed content creation for fields containing more than 255 characters by using ``TextField`` instead of ``CharField`` for all package model fields.
  `#7257 <https://pulp.plan.io/issues/7257>`_
- Fixed a bug where component path prefixes were added to package index paths twice instead of once when using structured publish.
  `#7295 <https://pulp.plan.io/issues/7295>`_


Improved Documentation
----------------------

- Added a note on per repository package uniqueness constraints to the feature overview documentation.
  `#6429 <https://pulp.plan.io/issues/6429>`_
- Fixed several URLs pointing at various API documentation.
  `#6506 <https://pulp.plan.io/issues/6506>`_
- Reworked the workflow documentation and added flow charts.
  `#7148 <https://pulp.plan.io/issues/7148>`_
- Completely refactored the documentation source files.
  `#7211 <https://pulp.plan.io/issues/7211>`_
- Added a high level "feature overview" documentation.
  `#7318 <https://pulp.plan.io/issues/7318>`_
- Added meaningful endpoint descriptions to the REST API documentation.
  `#7355 <https://pulp.plan.io/issues/7355>`_


Misc
----

- Added tests for repos with distribution paths that are not equal to the codename.
  `#6051 <https://pulp.plan.io/issues/6051>`_
- Added a long_description to the python package.
  `#6882 <https://pulp.plan.io/issues/6882>`_
- Added test to publish repository with package index files but no packages.
  `#7344 <https://pulp.plan.io/issues/7344>`_


----


2.5.0b1 (2020-07-15)
====================

Features
--------


- Added additional metadata fields to published Release files.
  `#6907 <https://pulp.plan.io/issues/6907>`_



Bugfixes
--------


- Fixed a bug where some nullable fields for remotes could not be set to null via the API.
  `#6908 <https://pulp.plan.io/issues/6908>`_
- Fixed a bug where APT client was installing same patches again and again.
  `#6982 <https://pulp.plan.io/issues/6982>`_



Misc
----


- Renamed some internal models to Apt.. to keep API consistent with other plugins.
  `#6897 <https://pulp.plan.io/issues/6897>`_



----


2.4.0b1 (2020-06-17)
====================

Features
--------


- The "Date" field is now added to Release files during publish.
  `#6869 <https://pulp.plan.io/issues/6869>`_



Bugfixes
--------


- Fixed structured publishing of architecture 'all' type packages.
  `#6787 <https://pulp.plan.io/issues/6787>`_
- Fixed a bug where published Release files were using paths relative to the repo root, instead of relative to the release file.
  `#6876 <https://pulp.plan.io/issues/6876>`_



----


2.3.0b1 (2020-04-29)
====================

Features
--------


- Added Release file signing using signing services.
  `#6171 <https://pulp.plan.io/issues/6171>`_



Bugfixes
--------


- Fixed synchronization of Release files without a Suite field.
  `#6050 <https://pulp.plan.io/issues/6050>`_
- Fixed publication creation with packages referenced from multiple package inecies.
  `#6383 <https://pulp.plan.io/issues/6383>`_



Improved Documentation
----------------------


- Documented bindings installation for the dev environment.
  `#6396 <https://pulp.plan.io/issues/6396>`_



Misc
----


- Added tests for invalid Debian repositories (bad signature, missing package indecies).
  `#6052 <https://pulp.plan.io/issues/6052>`_
- Made tests use the bindings config from pulp-smash.
  `#6393 <https://pulp.plan.io/issues/6393>`_



----


2.2.0b1 (2020-03-03)
====================

Features
--------


- Structured publishing (with releases and components) has been implemented.
  `#6029 <https://pulp.plan.io/issues/6029>`_
- Verification of upstream signed metadata has been implemented.
  `#6170 <https://pulp.plan.io/issues/6170>`_



----


2.0.0b3 (2019-11-14)
====================

Features
--------


- Change `relative_path` from `CharField` to `TextField`
  `#4544 <https://pulp.plan.io/issues/4544>`_
- Add more validation for uploading packages and installer packages.
  `#5377 <https://pulp.plan.io/issues/5377>`_



Deprecations and Removals
-------------------------


- Change `_id`, `_created`, `_last_updated`, `_href` to `pulp_id`, `pulp_created`, `pulp_last_updated`, `pulp_href`
  `#5457 <https://pulp.plan.io/issues/5457>`_
- Remove "_" from `_versions_href`, `_latest_version_href`
  `#5548 <https://pulp.plan.io/issues/5548>`_
- Removing base field: `_type` .
  `#5550 <https://pulp.plan.io/issues/5550>`_
- Sync is no longer available at the {remote_href}/sync/ repository={repo_href} endpoint. Instead, use POST {repo_href}/sync/ remote={remote_href}.

  Creating / listing / editing / deleting deb repositories is now performed on /pulp/api/v3/repositories/deb/apt/ instead of /pulp/api/v3/repositories/.
  `#5698 <https://pulp.plan.io/issues/5698>`_



Bugfixes
--------


- Fix `fields` filter.
  `#5543 <https://pulp.plan.io/issues/5543>`_



Misc
----


- Depend on pulpcore, directly, instead of pulpcore-plugin.
  `#5580 <https://pulp.plan.io/issues/5580>`_



----


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
