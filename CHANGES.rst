.. _changelog:

================================================================================
Changelog
================================================================================

..
   You should *NOT* be adding new change log entries to this file, this file is managed by towncrier.
   You *may* edit previous change logs to correct typos or similar.
   To learn how to add new entries see the 'Changelog Update' heading in the CONTRIBUTING.rst file.

   WARNING: Don't drop the next directive!

.. towncrier release notes start

2.21.1 (2023-07-20)
===================

Bugfixes
--------

- Fixed KeyError during publish if package has architecture that's not supported in the Packages file.
  Instead, a warning message will be logged.
  `#777 <https://github.com/pulp/pulp_deb/issues/777>`_
- Fixed an async error preventing synchronization with ``sync_installer`` set to ``True``.
  `#797 <https://github.com/pulp/pulp_deb/issues/797>`_
- Fixed content creating code triggered in rare edge cases when unapplying DB migration 0021.
  `#806 <https://github.com/pulp/pulp_deb/issues/806>`_
- Fixed a bug where structured package upload was only working as intended for the first package uploaded to each repository.
  Also added logging and ensured structure content is added to the creating tasks ``created_resources`` list.
  `#807 <https://github.com/pulp/pulp_deb/issues/807>`_


----


2.21.0 (2023-05-22)
===================

Features
--------

- The upload of content has been changed to accept already existing debian packages. This allows multiple users to own identical files.
  `#592 <https://github.com/pulp/pulp_deb/issues/592>`_
- Sign the metadata for all releases in a repo concurrently, greatly speeding up the publish task in environments where signing is slow.
  `#682 <https://github.com/pulp/pulp_deb/issues/682>`_
- Add new parameters `component` and `distribution` to the package upload endpoint to enable a structured package upload.
  `#743 <https://github.com/pulp/pulp_deb/issues/743>`_
- Declare and require at least pulpcore/3.25 compatibility.
  `#770 <https://github.com/pulp/pulp_deb/issues/770>`_


Bugfixes
--------

- Improve the pulp_deb "No valid Release file found" error message for gpg validation fail.
  `#399 <https://github.com/pulp/pulp_deb/issues/399>`_
- Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
  `#612 <https://github.com/pulp/pulp_deb/issues/612>`_
- Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
  or more releases.
  `#674 <https://github.com/pulp/pulp_deb/issues/674>`_
- Fixed a bug that prevented orphan cleanup due to protected foreign keys.
  `#690 <https://github.com/pulp/pulp_deb/issues/690>`_
- Fixed bug where PackageReleaseComponents were not being automatically removed when dupes were added
  to a repo version even though the duplicate Packages they referenced were being removed.
  `#705 <https://github.com/pulp/pulp_deb/issues/705>`_


Improved Documentation
----------------------

- Improved the documentation on metadata signing.
  `#660 <https://github.com/pulp/pulp_deb/issues/660>`_
- Fixed infinite loading when searching for specific terms.
  `#765 <https://github.com/pulp/pulp_deb/issues/765>`_


Removals
--------

- Package and generic content API endpoints no longer return errors when entities already exist.
  Instead they return the existing entities as if they had just been created.
  `#592 <https://github.com/pulp/pulp_deb/issues/592>`_
- Replaced the ``release`` field with the triple ``distribution``, ``codename``, ``suite`` on the ``/pulp/pulp/api/v3/content/deb/release_components/`` and ``/pulp/pulp/api/v3/content/deb/release_architectures/`` API endpoints.
  As a result, the available filters where also adjusted for the new fields.
  `#748 <https://github.com/pulp/pulp_deb/issues/748>`_


Misc
----

- Add precompiled test data for pytest to use in functional tests
  `#395 <https://github.com/pulp/pulp_deb/issues/395>`_
- Made repository publication structure independed of the Release model, which includes removing all foreighn key relations to the model.
  `#748 <https://github.com/pulp/pulp_deb/issues/748>`_


----


2.20.3 (2023-07-20)
===================

Bugfixes
--------

- Fixed KeyError during publish if package has architecture that's not supported in the Packages file.
  Instead, a warning message will be logged.
  `#777 <https://github.com/pulp/pulp_deb/issues/777>`_
- Fixed an async error preventing synchronization with ``sync_installer`` set to ``True``.
  `#797 <https://github.com/pulp/pulp_deb/issues/797>`_


Improved Documentation
----------------------

- Fixed infinite loading when searching for specific terms.
  `#765 <https://github.com/pulp/pulp_deb/issues/765>`_


----


2.20.2 (2023-04-26)
===================

Bugfixes
--------

- Fixed a bug that prevented orphan cleanup due to protected foreign keys.
  `#690 <https://github.com/pulp/pulp_deb/issues/690>`_


Misc
----

- Add precompiled test data for pytest to use in functional tests
  `#395 <https://github.com/pulp/pulp_deb/issues/395>`_


----


2.20.1 (2022-12-07)
===================

Bugfixes
--------

- Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
  `#612 <https://github.com/pulp/pulp_deb/issues/612>`_
- Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
  or more releases.
  `#674 <https://github.com/pulp/pulp_deb/issues/674>`_


----


2.20.0 (2022-10-19)
===================

Features
--------

- Added the option to synchronize repositories using an optimized mode (enabled by default).
  `#564 <https://github.com/pulp/pulp_deb/issues/564>`_
- Added feature to import/export pulp_deb content
  `#605 <https://github.com/pulp/pulp_deb/issues/605>`_


Bugfixes
--------

- Fixed handling of download URLs containing special characters in the path part.
  `#571 <https://github.com/pulp/pulp_deb/issues/571>`_
- Fixed several serializer bugs preventing the manual creation of structure content of type
  ``ReleaseArchitecture``, ``ReleaseComponent``, and ``PackageReleaseComponent``.
  `#575 <https://github.com/pulp/pulp_deb/issues/575>`_
- Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
  `#601 <https://github.com/pulp/pulp_deb/issues/601>`_
- Added a better error message when users try to create a repository version containing duplicate APT distributions.
  `#603 <https://github.com/pulp/pulp_deb/issues/603>`_
- Fixed a bug preventing the synchronization of repos referencing a single package from multiple package indices.
  `#632 <https://github.com/pulp/pulp_deb/issues/632>`_


Improved Documentation
----------------------

- Added workflow docs on manually creating structured repos.
  `#586 <https://github.com/pulp/pulp_deb/issues/586>`_
- Added feature overview documentation for the new Import/Export feature.
  `#624 <https://github.com/pulp/pulp_deb/issues/624>`_


Misc
----

- Add a proper local SigningService setup for tests using pytest.
  `#402 <https://github.com/pulp/pulp_deb/issues/402>`_


----


2.19.3 (2022-12-07)
===================

Bugfixes
--------

- Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
  `#612 <https://github.com/pulp/pulp_deb/issues/612>`_
- Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
  or more releases.
  `#674 <https://github.com/pulp/pulp_deb/issues/674>`_


----


2.19.2 (2022-10-18)
===================

Bugfixes
--------

- Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
  `#601 <https://github.com/pulp/pulp_deb/issues/601>`_
- Added a better error message when users try to create a repository version containing duplicate APT distributions.
  `#603 <https://github.com/pulp/pulp_deb/issues/603>`_


Improved Documentation
----------------------

- Added workflow docs on manually creating structured repos.
  `#586 <https://github.com/pulp/pulp_deb/issues/586>`_


----


2.19.1 (2022-07-25)
===================

Bugfixes
--------

- Fixed handling of download URLs containing special characters in the path part.
  `#571 <https://github.com/pulp/pulp_deb/issues/571>`_
- Fixed several serializer bugs preventing the manual creation of structure content of type
  ``ReleaseArchitecture``, ``ReleaseComponent``, and ``PackageReleaseComponent``.
  `#575 <https://github.com/pulp/pulp_deb/issues/575>`_


----


2.19.0 (2022-06-23)
===================

Bugfixes
--------

- Added support for uploading zstd compressed packages.
  `#459 <https://github.com/pulp/pulp_deb/issues/459>`_
- Fixed a bug causing inconsistent verbatim publications in combination with rare circumstances and streamed syncs.
  `#549 <https://github.com/pulp/pulp_deb/issues/549>`_


Misc
----

- Converted CharField to TextField for pulp_deb models.
  `#532 <https://github.com/pulp/pulp_deb/issues/532>`_


----


2.18.3 (2022-12-07)
===================

Bugfixes
--------

- Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
  `#612 <https://github.com/pulp/pulp_deb/issues/612>`_
- Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
  or more releases.
  `#674 <https://github.com/pulp/pulp_deb/issues/674>`_


----


2.18.2 (2022-10-18)
===================

Bugfixes
--------

- Added a better error message when users try to create a repository version containing duplicate APT distributions.
  `#603 <https://github.com/pulp/pulp_deb/issues/603>`_


----


2.18.1 (2022-08-16)
===================

Bugfixes
--------

- Fixed handling of download URLs containing special characters in the path part.
  `#571 <https://github.com/pulp/pulp_deb/issues/571>`_
- Fixed several serializer bugs preventing the manual creation of structure content of type
  ``ReleaseArchitecture``, ``ReleaseComponent``, and ``PackageReleaseComponent``.
  `#575 <https://github.com/pulp/pulp_deb/issues/575>`_
- Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
  `#601 <https://github.com/pulp/pulp_deb/issues/601>`_


----


2.18.0 (2022-04-21)
===================

Features
--------

- Added experimental advanced copy API with support for structured copying.
  `#396 <https://github.com/pulp/pulp_deb/issues/396>`_


Bugfixes
--------

- Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
  `#422 <https://github.com/pulp/pulp_deb/issues/422>`_
- Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
  You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
  `#443 <https://github.com/pulp/pulp_deb/issues/443>`_


Misc
----

- Reworked the sync handling for upstream repos using ``No-Support-for-Architecture-all: Packages`` format.
  This was needed to avoid clashes with the new arch filtering introduced in `#422 <https://github.com/pulp/pulp_deb/issues/422>`_.
  `#456 <https://github.com/pulp/pulp_deb/issues/456>`_


----


2.17.2 (2022-10-18)
===================

Bugfixes
--------

- Fixed handling of download URLs containing special characters in the path part.
  `#571 <https://github.com/pulp/pulp_deb/issues/571>`__
- Fixed several serializer bugs preventing the manual creation of structure content of type
  ``ReleaseArchitecture``, ``ReleaseComponent``, and ``PackageReleaseComponent``.
  `#575 <https://github.com/pulp/pulp_deb/issues/575>`__
- Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
  `#601 <https://github.com/pulp/pulp_deb/issues/601>`__
- Added a better error message when users try to create a repository version containing duplicate APT distributions.
  `#603 <https://github.com/pulp/pulp_deb/issues/603>`__


----


2.17.1 (2022-04-21)
===================

Bugfixes
--------

- Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
  `#422 <https://github.com/pulp/pulp_deb/issues/422>`__
- Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
  You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
  `#443 <https://github.com/pulp/pulp_deb/issues/443>`__


Misc
----

- Reworked the sync handling for upstream repos using ``No-Support-for-Architecture-all: Packages`` format.
  This was needed to avoid clashes with the new arch filtering introduced in `#422 <https://github.com/pulp/pulp_deb/issues/422>`_.
  `#456 <https://github.com/pulp/pulp_deb/issues/456>`__


----


2.17.0 (2022-01-11)
===================

Features
--------

- Users can now use the FORCE_IGNORE_MISSING_PACKAGE_INDICES setting to define the corresponding behaviour for all remotes.
  `#9555 <https://pulp.plan.io/issues/9555>`_


Bugfixes
--------

- Fixed mirrored metadata handling when creating a new repository version.
  `#8756 <https://pulp.plan.io/issues/8756>`_
- Fixed a bug causing package validation to fail, when the package paragraph contains keys without values.
  `#8770 <https://pulp.plan.io/issues/8770>`_
- Fixed a bug causing publications to reference any ``AptReleaseSigningService`` via a full URL instead of just a ``pulp_href``.
  `#9563 <https://pulp.plan.io/issues/9563>`_


----


2.16.3 (2022-10-18)
===================

Bugfixes
--------

- Fixed handling of download URLs containing special characters in the path part.
  `#571 <https://github.com/pulp/pulp_deb/issues/571>`__
- Fixed several serializer bugs preventing the manual creation of structure content of type
  ``ReleaseArchitecture``, ``ReleaseComponent``, and ``PackageReleaseComponent``.
  `#575 <https://github.com/pulp/pulp_deb/issues/575>`__
- Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
  `#601 <https://github.com/pulp/pulp_deb/issues/601>`__
- Added a better error message when users try to create a repository version containing duplicate APT distributions.
  `#603 <https://github.com/pulp/pulp_deb/issues/603>`__


----


2.16.2 (2022-04-21)
===================

Features
--------

- Users can now use the FORCE_IGNORE_MISSING_PACKAGE_INDICES setting to define the corresponding behaviour for all remotes.
  `#9555 <https://github.com/pulp/pulp_deb/issues/9555>`__


Bugfixes
--------

- Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
  `#422 <https://github.com/pulp/pulp_deb/issues/422>`__
- Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
  You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
  `#443 <https://github.com/pulp/pulp_deb/issues/443>`__


Misc
----

- Reworked the sync handling for upstream repos using ``No-Support-for-Architecture-all: Packages`` format.
  This was needed to avoid clashes with the new arch filtering introduced in `#422 <https://github.com/pulp/pulp_deb/issues/422>`_.
  `#456 <https://github.com/pulp/pulp_deb/issues/456>`__


----


2.16.1 (2022-01-13)
===================

Bugfixes
--------

- Fixed a bug causing package validation to fail, when the package paragraph contains keys without values.
  (backported from #8770)
  `#432 <https://github.com/pulp/pulp_deb/issues/432>`_
- Fixed a bug causing publications to reference any ``AptReleaseSigningService`` via a full URL instead of just a ``pulp_href``.
  (backported from #9563)
  `#433 <https://github.com/pulp/pulp_deb/issues/433>`_


----


2.16.0 (2021-10-28)
===================

Bugfixes
--------

- Flat repo syncs were made more robust with respect to minimal release files.
  `#7673 <https://pulp.plan.io/issues/7673>`_
- Fixed a bug causing syncs to fail if upstream repos have more than 256 characters worth of distributions, components, or architectures.
  `#9277 <https://pulp.plan.io/issues/9277>`_
- Added fix to delete package fields with values of an incorrect type.
  `#9333 <https://pulp.plan.io/issues/9333>`_


Misc
----

- Amended dispatch arguments deprecated by pulpcore in anticipation of removal.
  `#9349 <https://pulp.plan.io/issues/9349>`_


----


2.15.1 (2021-10-27)
===================

Misc
----

- Amended dispatch arguments deprecated by pulpcore in anticipation of removal.
  (backported from #9349)
  `#9505 <https://pulp.plan.io/issues/9505>`_


----


2.15.0 (2021-08-26)
===================

Features
--------

- Add custom_fields to hold non-standard PackageIndex fields
  `#8232 <https://pulp.plan.io/issues/8232>`_


Bugfixes
--------

- The plugins async pipeline was made Django 3 compatible in anticipation of pulpcore 3.15.
  `#9299 <https://pulp.plan.io/issues/9299>`_


Improved Documentation
----------------------

- Reworked the plugin installation docs to be helpful to new users.
  `#9186 <https://pulp.plan.io/issues/9186>`_


Misc
----

- Added touch statements to prevent false positives during orphan cleanup.
  `#9162 <https://pulp.plan.io/issues/9162>`_
- Replaced deprecated JSONField model from contrib with the one available with Django 3.
  `#9300 <https://pulp.plan.io/issues/9300>`_


----


2.14.1 (2021-07-29)
===================

Compatible with: ``pulpcore>=3.14,<3.16``

Misc
----

- Re-enabled Python 3.6 and 3.7 for the all 2.14.* releases.
  `#9164 <https://pulp.plan.io/issues/9164>`_
- Added touch statements to prevent false positives during orphan cleanup.
  (backported from #9162)
  `#9175 <https://pulp.plan.io/issues/9175>`_


----


2.14.0 (2021-07-22)
===================

.. warning::
   This version was released in a broken state and has been yanked from pypi.
   The issues are addressed in the 2.14.1 release.

Bugfixes
--------

- Add missing "Size" field in publications
  `#8506 <https://pulp.plan.io/issues/8506>`_
- Fixed a bug where arch=all package indices were not being synced when filtering by architecture.
  `#8910 <https://pulp.plan.io/issues/8910>`_


Removals
--------

- Dropped support for Python 3.6 and 3.7. pulp_deb now supports Python 3.8+.
  `#9036 <https://pulp.plan.io/issues/9036>`_


Misc
----

- If remotes specify components or architectures that do not exist in the synchronized Release file, a warning is now logged.
  `#6948 <https://pulp.plan.io/issues/6948>`_


----


2.13.1 (2021-08-02)
===================

Compatible with: ``pulpcore>=3.12,<3.15``

Bugfixes
--------

- Add missing "Size" field in publications
  (backported from #8506)
  `#9167 <https://pulp.plan.io/issues/9167>`_


----


2.13.0 (2021-05-27)
===================

Compatible with: ``pulpcore>=3.12,<3.15``

Bugfixes
--------

- Completely disabled translation file synchronization to prevent sync failures.
  `#8671 <https://pulp.plan.io/issues/8671>`_
- Fixed a bug where components from the remote were being ignored when specified as the plain component.
  `#8828 <https://pulp.plan.io/issues/8828>`_


----


2.12.1 (2021-05-25)
===================

Compatible with: ``pulpcore>=3.12,<3.14``

Bugfixes
--------

- Completely disabled translation file synchronization to prevent sync failures.
  (Backported from https://pulp.plan.io/issues/8671)
  `#8735 <https://pulp.plan.io/issues/8735>`_


----


2.12.0 (2021-05-10)
===================

Compatible with: ``pulpcore>=3.12,<3.14``

Features
--------

- APT repositories may now reference an APT remote, that will automatically be used for syncs.
  `#8520 <https://pulp.plan.io/issues/8520>`_


Bugfixes
--------

- Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
  `#8410 <https://pulp.plan.io/issues/8410>`_


Misc
----

- Migrated to new Distribution model for pulpcore 3.13 compatibility.
  `#8682 <https://pulp.plan.io/issues/8682>`_


----


2.11.2 (2021-05-25)
===================

Compatible with: ``pulpcore>=3.10,<3.13``

Bugfixes
--------

- Completely disabled translation file synchronization to prevent sync failures.
  (Backported from https://pulp.plan.io/issues/8671)
  `#8736 <https://pulp.plan.io/issues/8736>`_


----


2.11.1 (2021-04-14)
===================

Compatible with: ``pulpcore>=3.10,<3.13``

Bugfixes
--------

- Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
  (Backported from https://pulp.plan.io/issues/8410)
  `#8556 <https://pulp.plan.io/issues/8556>`_


----


2.11.0 (2021-03-30)
===================

Compatible with: ``pulpcore>=3.10,<3.13``

No significant changes.


----


2.10.2 (2021-05-25)
===================

Compatible with: ``pulpcore>=3.10,<3.12``

Bugfixes
--------

- Completely disabled translation file synchronization to prevent sync failures.
  (Backported from https://pulp.plan.io/issues/8671)
  `#8737 <https://pulp.plan.io/issues/8737>`_


----


2.10.1 (2021-04-14)
===================

Compatible with: ``pulpcore>=3.10,<3.12``

Bugfixes
--------

- Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
  (Backported from https://pulp.plan.io/issues/8410)
  `#8558 <https://pulp.plan.io/issues/8558>`_


----


2.10.0 (2021-03-17)
===================

Compatible with: ``pulpcore>=3.10,<3.12``

Bugfixes
--------

- Ensured the plugin respects the ALLOWED_CONTENT_CHECKSUMS setting.
  `#8388 <https://pulp.plan.io/issues/8388>`_


Improved Documentation
----------------------

- The plugin documentation was moved from https://pulp-deb.readthedocs.io/ to https://docs.pulpproject.org/pulp_deb/.
  `#8113 <https://pulp.plan.io/issues/8113>`_
- Added workflow documentation on checksum handling configuration.
  `#8388 <https://pulp.plan.io/issues/8388>`_


Removals
--------

- Update AptReleaseSigningService validation to respect new base class requirements.
  `#8307 <https://pulp.plan.io/issues/8307>`_


----


2.9.3 (2021-11-16)
==================

Misc
----

- Added an upper bound of ``<0.1.42`` to the ``python-debian`` dependency to prevent breakage against python ``<3.7``.


----


2.9.2 (2021-05-25)
==================

Compatible with: ``pulpcore>=3.7,<3.11``

Bugfixes
--------

- Completely disabled translation file synchronization to prevent sync failures.
  (Backported from https://pulp.plan.io/issues/8671)
  `#8738 <https://pulp.plan.io/issues/8738>`_


----


2.9.1 (2021-04-14)
==================

Compatible with: ``pulpcore>=3.7,<3.11``

Bugfixes
--------

- Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
  (Backported from https://pulp.plan.io/issues/8410)
  `#8559 <https://pulp.plan.io/issues/8559>`_


----


2.9.0 (2021-01-14)
==================

Compatible with: ``pulpcore>=3.7,<3.11``


----


2.8.0 (2020-11-23)
==================

Compatible with: ``pulpcore>=3.7,<3.10``

Features
--------

- Added an ``ignore_missing_package_indices`` flag to remotes which users may set to allow the synchronization of repositories with missing declared package indices.
  `#7467 <https://pulp.plan.io/issues/7467>`_
- Added the capability to synchronize repositories using "flat repository format".
  `#7502 <https://pulp.plan.io/issues/7502>`_
- Added ability to handle upstream repositories without a "Codename" field.
  `#7886 <https://pulp.plan.io/issues/7886>`_


----


2.7.0 (2020-09-29)
==================

Compatible with: ``pulpcore>=3.7,<3.9``


----


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


2.0.0b4 (2020-01-14)
====================

No significant changes.


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
