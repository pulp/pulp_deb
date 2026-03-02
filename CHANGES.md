# Changelog

[//]: # (You should *NOT* be adding new change log entries to this file, this)
[//]: # (file is managed by towncrier. You *may* edit previous change logs to)
[//]: # (fix problems like typo corrections or such.)
[//]: # (To add a new change log entry, please see the contributing docs.)
[//]: # (WARNING: Don't drop the towncrier directive!)

[//]: # (towncrier release notes start)

## 3.8.1 (2026-01-08) {: #3.8.1 }

#### Features {: #3.8.1-feature }

- Bump pulpcore upperbound to <3.115.

#### Bugfixes {: #3.8.1-bugfix }

- Teach modelresource.render it might get a `value` of None.

  This prepares us to handle a django-import-export/4 codepath.

---

## 3.8.0 (2025-11-04) {: #3.8.0 }

#### Features {: #3.8.0-feature }

- Added autopublish functionality.
  Creates a structured APT publication when used.
  Cannot be used to create verbatim publications.
  [#406](https://github.com/pulp/pulp_deb/issues/406)
- Add support for Alternate Content Sources (ACS)
  [#1347](https://github.com/pulp/pulp_deb/issues/1347)

#### Bugfixes {: #3.8.0-bugfix }

- Allow pulp-import-export when domains are enabled.
- Fixed a compatibility bug on source package upload with pulpcore 3.86.

#### Misc {: #3.8.0-misc }

- Terminate gpg-agent after private key import to avoid race condition on cleanup.
  [#1332](https://github.com/pulp/pulp_deb/issues/1332)

---

## 3.7.1 (2026-02-26) {: #3.7.1 }

#### Bugfixes {: #3.7.1-bugfix }

- Allow pulp-import-export when domains are enabled.
- Fixed a compatibility bug on source package upload with pulpcore 3.86.
- Teach modelresource.render it might get a `value` of None.

  This prepares us to handle a django-import-export/4 codepath.

---

## 3.7.0 (2025-08-20) {: #3.7.0 }

#### Bugfixes {: #3.7.0-bugfix }

- CopyContent between repository-versions with same distribution-name but different Release content-units fails. Fixed by not copying Release content-unit for distribution-name that already is present in target-version.
  [#1309](https://github.com/pulp/pulp_deb/issues/1309)

---

## 3.6.0 (2025-08-04) {: #3.6.0 }

#### Features {: #3.6.0-feature }

- Enabled the checkpoint feature in pulp_deb.
  [#1250](https://github.com/pulp/pulp_deb/issues/1250)
- Added support for Domains.
  [#1253](https://github.com/pulp/pulp_deb/issues/1253)
- Syncing flat repositories will now always publish distribution "flat-repo".
  [#1258](https://github.com/pulp/pulp_deb/issues/1258)

#### Bugfixes {: #3.6.0-bugfix }

- Fix bug where sync failed if a custom field in Package index was blank.
  [#1225](https://github.com/pulp/pulp_deb/issues/1225)
- Flat repo syncs no longer consider the Release file for download as part of package index creation, avoiding unnecessary downloads as well as a rare edge case where the sync fails with a duplicate-path error if the Release file references itself with a checksum that already exists as an artifact within Pulp.
  [#1279](https://github.com/pulp/pulp_deb/issues/1279)

---

## 3.5.4 (2026-02-26) {: #3.5.4 }

#### Bugfixes {: #3.5.4-bugfix }

- Allow pulp-import-export when domains are enabled.
- Teach modelresource.render it might get a `value` of None.

  This prepares us to handle a django-import-export/4 codepath.

---

## 3.5.3 (2025-09-18) {: #3.5.3 }

#### Bugfixes {: #3.5.3-bugfix }

- Flat repo syncs no longer consider the Release file for download as part of package index creation, avoiding unnecessary downloads as well as a rare edge case where the sync fails with a duplicate-path error if the Release file references itself with a checksum that already exists as an artifact within Pulp.
  [#1279](https://github.com/pulp/pulp_deb/issues/1279)
- Fixed a compatibility bug on source package upload with pulpcore 3.86.

---

## 3.5.2 (2025-04-23) {: #3.5.2 }

#### Features {: #3.5.1-feature }

- Added compatibility with pulpcore 3.70+.

---

## 3.5.1 (2025-02-24) {: #3.5.1 }

#### Features {: #3.5.1-feature }

- Added compatibility with pulpcore 3.70+.

---

## 3.5.0 (2025-01-22) {: #3.5.0 }

#### Features {: #3.5.0-feature }

- Added initial RBAC support.
  [#860](https://github.com/pulp/pulp_deb/issues/860)
- Exposed the plain component when retrieving ReleaseComponent content via the API.
  [#1167](https://github.com/pulp/pulp_deb/issues/1167)
- Expose a sha256 column for source packages that contains the digest of the dsc file.

#### Bugfixes {: #3.5.0-bugfix }

- Fixed an issue where the signing service did not properly clean up temporary files after completion.
  [#1141](https://github.com/pulp/pulp_deb/issues/1141)
- Removing packages from a repository using the modify API endpoint now also removes all associated PackageReleaseComponents.
  [#1190](https://github.com/pulp/pulp_deb/issues/1190)

#### Misc {: #3.5.0-misc }

- Rebase migrations to prepare for pulpcore 3.70.
  [#1204](https://github.com/pulp/pulp_deb/issues/1204)

---

## 3.4.0 (2024-10-02) {: #3.4.0 }

#### Features {: #3.4.0-feature }

- Extend publishing at by-hash paths to source files.
  [#1059](https://github.com/pulp/pulp_deb/issues/1059)
- Improved performance when creating publications, by creating PublishedArtifacts in bulk, greatly reducing the number of database calls.
  [#1147](https://github.com/pulp/pulp_deb/issues/1147)
- Improved performance by prefetching relevant Artifacts and RemoteArtifacts during publishing, reducing the number of database calls.
  [#1148](https://github.com/pulp/pulp_deb/issues/1148)

#### Bugfixes {: #3.4.0-bugfix }

- Fixed throwing the wrong error when pointing to an invalid repository with a custom signing service.
  [#1122](https://github.com/pulp/pulp_deb/issues/1122)

#### Misc {: #3.4.0-misc }

- Improved the publish task performance by optimizing the database queries used in that task.
  [#1115](https://github.com/pulp/pulp_deb/issues/1115)

---

## 3.3.1 (2024-08-06) {: #3.3.1 }

#### Bugfixes {: #3.3.1-bugfix }

- Fixed throwing the wrong error when pointing to an invalid repository with a custom signing service.
  [#1122](https://github.com/pulp/pulp_deb/issues/1122)

#### Misc {: #3.3.1-misc }

- Improved the publish task performance by optimizing the database queries used in that task.
  [#1115](https://github.com/pulp/pulp_deb/issues/1115)

---

## 3.3.0 (2024-06-19) {: #3.3.0 }


#### Features {: #3.3.0-feature }

- Added the ``architectures`` and ``components`` parameters to the release API in order to create releases with accompanying architectures and components in a single API call.
  Also added retrieve functionality to the release API.
  [#1038](https://github.com/pulp/pulp_deb/issues/1038)
- Added support for duplicate source debs. If an source deb already exists, return it instead of raising an exception.
  [#1077](https://github.com/pulp/pulp_deb/issues/1077)
- Made the plugin compatible with pulpcore 3.55.0+.
  [#1100](https://github.com/pulp/pulp_deb/issues/1100)

#### Bugfixes {: #3.3.0-bugfix }

- Fixed a bug where an ``IntegrityError`` was raised during publish when a source package belonged to
  two dists.
  [#1053](https://github.com/pulp/pulp_deb/issues/1053)

#### Improved Documentation {: #3.3.0-doc }

- Added initial staging docs.
  [#1014](https://github.com/pulp/pulp_deb/issues/1014)

#### Removals {: #3.3.0-removal }

- When creating a release, the API now returns a task instead of the release being created.
  In addition, attempting to create a release that already exists will no longer return an error.
  Instead the resulting task will simply list the existing content in its ``created_resources`` field.
  [#1038](https://github.com/pulp/pulp_deb/issues/1038)
- Dropped support for Python 3.8. pulp_deb now supports Python >=3.9.
  [#1039](https://github.com/pulp/pulp_deb/issues/1039)
- When uploading a source deb that already exists, instead of throwing an exception it will now return the existing source package.
  [#1077](https://github.com/pulp/pulp_deb/issues/1077)

---

## 3.2.1 (2024-08-06) {: #3.2.1 }

#### Bugfixes {: #3.2.1-bugfix }

- Fixed a bug where an ``IntegrityError`` was raised during publish when a source package belonged to
  two dists.
  [#1053](https://github.com/pulp/pulp_deb/issues/1053)
- Fixed throwing the wrong error when pointing to an invalid repository with a custom signing service.
  [#1122](https://github.com/pulp/pulp_deb/issues/1122)

#### Misc {: #3.2.1-misc }

- Improved the publish task performance by optimizing the database queries used in that task.
  [#1115](https://github.com/pulp/pulp_deb/issues/1115)

---

## 3.2.0 (2024-03-04) {: #3.2.0 }

### Features

-   Added feature to serve published artifacts from previous publications for 3 days.
    This fulfills the apt-by-hash/acquire-by-hash spec by allowing by-hash files to be cached for a
    period of 3 days.
    [#911](https://github.com/pulp/pulp_deb/issues/911)
-   Added retrieve functionality for ReleaseArchitecture and ReleaseComponent content.
    [#1010](https://github.com/pulp/pulp_deb/issues/1010)
-   Allow optimize with mirror mode if nothing at all has changed in the repository being synced.
    [#1027](https://github.com/pulp/pulp_deb/issues/1027)

### Bugfixes

-   Fixed repo uniqueness constraints.
    Duplicate packages with identical checksums are now allowed.
    In addition, duplicates are now also handled for the set of incoming content.
    [#921](https://github.com/pulp/pulp_deb/issues/921)
-   Fixed a bug where pulp_deb was serving unpublished content when distributing a repository that has content but no publications.
    [#976](https://github.com/pulp/pulp_deb/issues/976)
-   Fixed a bug where enabling the `APT_BY_HASH` setting did not enable the feature.
    [#984](https://github.com/pulp/pulp_deb/issues/984)
-   Fixed DEBUG logging of prohibited duplicate packages.
    [#994](https://github.com/pulp/pulp_deb/issues/994)
-   Suppressed deb822's confusing log warning about python-apt not being installed.
    [#1019](https://github.com/pulp/pulp_deb/issues/1019)

### Removals

-   The API endpoints for ReleaseArchitecture and ReleaseComponent creation will no longer return a 400 `non_field_errors` if the content to be created already exists.
    Instead a task is triggered that will list the existing content in its `created_resources` field.
    [#1010](https://github.com/pulp/pulp_deb/issues/1010)

### Misc

-   Added tests that verify the download of content served by `pulp_deb`.
    [#919](https://github.com/pulp/pulp_deb/issues/919)
-   Added sync, publish and pulp2pulp performance tests to run with the nightly CI.
    [#970](https://github.com/pulp/pulp_deb/issues/970)

---

## 3.1.2 (2024-02-29) {: #3.1.2 }

### Bugfixes

-   Fixed a bug where enabling the `APT_BY_HASH` setting did not enable the feature.
    [#984](https://github.com/pulp/pulp_deb/issues/984)
-   Fixed DEBUG logging of prohibited duplicate packages.
    [#994](https://github.com/pulp/pulp_deb/issues/994)
-   Suppressed deb822's confusing log warning about python-apt not being installed.
    [#1019](https://github.com/pulp/pulp_deb/issues/1019)

---

## 3.1.1 (2023-12-12) {: #3.1.1 }

### Bugfixes

-   Fixed repo uniqueness constraints.
    Duplicate packages with identical checksums are now allowed.
    In addition, duplicates are now also handled for the set of incoming content.
    [#921](https://github.com/pulp/pulp_deb/issues/921)
-   Fixed a bug where pulp_deb was serving unpublished content when distributing a repository that has content but no publications.
    [#976](https://github.com/pulp/pulp_deb/issues/976)

### Misc

-   Added tests that verify the download of content served by `pulp_deb`.
    [#919](https://github.com/pulp/pulp_deb/issues/919)

---

## 3.1.0 (2023-11-09) {: #3.1.0 }

### Features

-   Add support for handling source packages.
    [#409](https://github.com/pulp/pulp_deb/issues/409)
-   Added an option to publish by-hash/ files to mitigate the Hash Sum Mismatch error in debian repos as specified here: <https://wiki.debian.org/DebianRepository/Format#indices_acquisition_via_hashsums_.28by-hash.29>.
    Use the APT_BY_HASH setting to enable this feature.
    [#795](https://github.com/pulp/pulp_deb/issues/795)
-   Fixed the `create_repositories=True` parameter for importing content.
    [#872](https://github.com/pulp/pulp_deb/issues/872)
-   Add additional package name filters such as `name__contains` and `name__startswith`.
    Check the REST docs for a complete list.
    [#909](https://github.com/pulp/pulp_deb/issues/909)
-   Added extra filters linking SourcePackages to Releases and ReleaseComponents.
    [#926](https://github.com/pulp/pulp_deb/issues/926)
-   Made the plugin compatible with pulpcore 3.40.1+.
    [#928](https://github.com/pulp/pulp_deb/issues/928)

### Bugfixes

-   Improved the performance of structured `/pulp/api/v3/deb/copy/` actions.
    [#870](https://github.com/pulp/pulp_deb/issues/870)
-   Optimize mode can now take effect, when switching from mirrored to not mirrored mode between syncs.
    [#903](https://github.com/pulp/pulp_deb/issues/903)

---

## 3.0.2 (2024-02-29) {: #3.0.2 }

### Bugfixes

-   Fixed DEBUG logging of prohibited duplicate packages.
    [#994](https://github.com/pulp/pulp_deb/issues/994)
-   Suppressed deb822's confusing log warning about python-apt not being installed.
    [#1019](https://github.com/pulp/pulp_deb/issues/1019)

---

## 3.0.1 (2023-12-12) {: #3.0.1 }

### Features

-   Fixed the `create_repositories=True` parameter for importing content.
    [#872](https://github.com/pulp/pulp_deb/issues/872)

### Bugfixes

-   Improved the performance of structured `/pulp/api/v3/deb/copy/` actions.
    [#870](https://github.com/pulp/pulp_deb/issues/870)
-   Optimize mode can now take effect, when switching from mirrored to not mirrored mode between syncs.
    [#903](https://github.com/pulp/pulp_deb/issues/903)
-   Fixed repo uniqueness constraints.
    Duplicate packages with identical checksums are now allowed.
    In addition, duplicates are now also handled for the set of incoming content.
    [#921](https://github.com/pulp/pulp_deb/issues/921)
-   Fixed a bug where pulp_deb was serving unpublished content when distributing a repository that has content but no publications.
    [#976](https://github.com/pulp/pulp_deb/issues/976)

### Misc

-   Added tests that verify the download of content served by `pulp_deb`.
    [#919](https://github.com/pulp/pulp_deb/issues/919)

---

## 3.0.0 (2023-09-05) {: #3.0.0 }

### Features

-   Added `version`, `origin`, `label`, and `description` fields to Releases.
    These fields can be set when creating new Releases via the API.
    Going forward, they will also be synced from upstream release files if present.
    [#449](https://github.com/pulp/pulp_deb/issues/449)
-   Specify and remember the Signing Services we want to use for each Repo / Release.
    [#641](https://github.com/pulp/pulp_deb/issues/641)
-   Added API filters to limit results by related pulp_deb content types.
    [#646](https://github.com/pulp/pulp_deb/issues/646)
-   Added the `publish_upstream_release_fields` field to the repository model.
    To avoid a breaking change in publication behaviour, existing repositories are populated with the setting set to `False`, while any newly created repostiroies will default to `True`.
    Whatever the value on the repository, it can be overriden when creating a new publication.
    [#793](https://github.com/pulp/pulp_deb/issues/793)

### Bugfixes

-   Fixed KeyError during publish if package has architecture that's not supported in the Packages file.
    Instead, a warning message will be logged.
    [#777](https://github.com/pulp/pulp_deb/issues/777)
-   Fixed an async error preventing synchronization with `sync_installer` set to `True`.
    [#797](https://github.com/pulp/pulp_deb/issues/797)
-   Fixed content creating code triggered in rare edge cases when unapplying DB migration 0021.
    [#806](https://github.com/pulp/pulp_deb/issues/806)
-   Fixed a bug where structured package upload was only working as intended for the first package uploaded to each repository.
    Also added logging and ensured structure content is added to the creating tasks `created_resources` list.
    [#807](https://github.com/pulp/pulp_deb/issues/807)

### Improved Documentation

-   Added `pulp-cli-deb` installation instructions.
    [#598](https://github.com/pulp/pulp_deb/issues/598)
-   Replaced references to the Pulp Ansible installer with references to the Pulp OCI images.
    [#779](https://github.com/pulp/pulp_deb/issues/779)
-   Added workflow documentation for creating and using signing services.
    [#867](https://github.com/pulp/pulp_deb/issues/867)
-   Completely reworked the "Feature Overview" and "Workflows" docs with an emphasise on Pulp CLI and structured content.
    [#886](https://github.com/pulp/pulp_deb/issues/886)

### Removals

-   Since release file fields including "Label" and "Version", are now synced from upstream repositories, we have dropped the PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION settings.
    This removes the ability to publish Pulp internal "Label" and "Version" values that never made much sense, and had been disabled by default since at least pulp_deb 2.18.0.
    [#449](https://github.com/pulp/pulp_deb/issues/449)
-   The codename and suite fields are removed from the ReleaseComponent and ReleaseArchitecture models and all associated filters and viewsets.
    [#599](https://github.com/pulp/pulp_deb/issues/599)
-   The `pulp/api/v3/publications/deb/apt/` API endpoint, used to require users to explicitly set at least one of `simple` or `structured` to `True` on the POST.
    The new behavior is to default to `structured=True` and `simple=False`.
    [#858](https://github.com/pulp/pulp_deb/issues/858)

### Misc

-   This change includes a large DB migration to drop 'codename' and 'suite' from the uniqueness constraints of all structure content.
    The migration will merge any resulting collisions and alter all records with a foreign key relation to the so eliminated content to point at the merge result instead.
    [#599](https://github.com/pulp/pulp_deb/issues/599)
-   Added test cases for advanced copy task.
    [#758](https://github.com/pulp/pulp_deb/issues/758)
-   Add tests for content filters, and make filters return empty list if Content not in RepoVersion instead of raising ValidationError.
    [#780](https://github.com/pulp/pulp_deb/issues/780)
-   Added better scoping for the pytest fixtures.
    [#790](https://github.com/pulp/pulp_deb/issues/790)
-   Removed the `pulp-smash` test dependency.
    [#796](https://github.com/pulp/pulp_deb/issues/796)
-   Converted the publish tests to use the pytest framework.
    [#828](https://github.com/pulp/pulp_deb/issues/828)
-   Converted the import/export tests to use the pytest framework.
    [#846](https://github.com/pulp/pulp_deb/issues/846)

---

## 2.21.2 (2023-09-05) {: #2.21.2 }

### Bugfixes

-   Fixed advanced copy due to pulpcore deprecations.
    [#869](https://github.com/pulp/pulp_deb/issues/869)

### Misc

-   Fixed the deb/copy/ API path for scenarios that modify the API root.
    [#879](https://github.com/pulp/pulp_deb/issues/879)

---

## 2.21.1 (2023-07-20) {: #2.21.1 }

### Bugfixes

-   Fixed KeyError during publish if package has architecture that's not supported in the Packages file.
    Instead, a warning message will be logged.
    [#777](https://github.com/pulp/pulp_deb/issues/777)
-   Fixed an async error preventing synchronization with `sync_installer` set to `True`.
    [#797](https://github.com/pulp/pulp_deb/issues/797)
-   Fixed content creating code triggered in rare edge cases when unapplying DB migration 0021.
    [#806](https://github.com/pulp/pulp_deb/issues/806)
-   Fixed a bug where structured package upload was only working as intended for the first package uploaded to each repository.
    Also added logging and ensured structure content is added to the creating tasks `created_resources` list.
    [#807](https://github.com/pulp/pulp_deb/issues/807)

---

## 2.21.0 (2023-05-22) {: #2.21.0 }

### Features

-   The upload of content has been changed to accept already existing debian packages. This allows multiple users to own identical files.
    [#592](https://github.com/pulp/pulp_deb/issues/592)
-   Sign the metadata for all releases in a repo concurrently, greatly speeding up the publish task in environments where signing is slow.
    [#682](https://github.com/pulp/pulp_deb/issues/682)
-   Add new parameters component and distribution to the package upload endpoint to enable a structured package upload.
    [#743](https://github.com/pulp/pulp_deb/issues/743)
-   Declare and require at least pulpcore/3.25 compatibility.
    [#770](https://github.com/pulp/pulp_deb/issues/770)

### Bugfixes

-   Improve the pulp_deb "No valid Release file found" error message for gpg validation fail.
    [#399](https://github.com/pulp/pulp_deb/issues/399)
-   Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
    [#612](https://github.com/pulp/pulp_deb/issues/612)
-   Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
    or more releases.
    [#674](https://github.com/pulp/pulp_deb/issues/674)
-   Fixed a bug that prevented orphan cleanup due to protected foreign keys.
    [#690](https://github.com/pulp/pulp_deb/issues/690)
-   Fixed bug where PackageReleaseComponents were not being automatically removed when dupes were added
    to a repo version even though the duplicate Packages they referenced were being removed.
    [#705](https://github.com/pulp/pulp_deb/issues/705)

### Improved Documentation

-   Improved the documentation on metadata signing.
    [#660](https://github.com/pulp/pulp_deb/issues/660)
-   Fixed infinite loading when searching for specific terms.
    [#765](https://github.com/pulp/pulp_deb/issues/765)

### Removals

-   Package and generic content API endpoints no longer return errors when entities already exist.
    Instead they return the existing entities as if they had just been created.
    [#592](https://github.com/pulp/pulp_deb/issues/592)
-   Replaced the `release` field with the triple `distribution`, `codename`, `suite` on the `/pulp/pulp/api/v3/content/deb/release_components/` and `/pulp/pulp/api/v3/content/deb/release_architectures/` API endpoints.
    As a result, the available filters where also adjusted for the new fields.
    [#748](https://github.com/pulp/pulp_deb/issues/748)

### Misc

-   Add precompiled test data for pytest to use in functional tests
    [#395](https://github.com/pulp/pulp_deb/issues/395)
-   Made repository publication structure independed of the Release model, which includes removing all foreighn key relations to the model.
    [#748](https://github.com/pulp/pulp_deb/issues/748)

---

## 2.20.4 (2023-09-05) {: #2.20.4 }

### Bugfixes

-   Improve the pulp_deb "No valid Release file found" error message for gpg validation fail.
    [#399](https://github.com/pulp/pulp_deb/issues/399)

### Misc

-   Fixed the deb/copy/ API path for scenarios that modify the API root.
    [#879](https://github.com/pulp/pulp_deb/issues/879)

---

## 2.20.3 (2023-07-20) {: #2.20.3 }

### Bugfixes

-   Fixed KeyError during publish if package has architecture that's not supported in the Packages file.
    Instead, a warning message will be logged.
    [#777](https://github.com/pulp/pulp_deb/issues/777)
-   Fixed an async error preventing synchronization with `sync_installer` set to `True`.
    [#797](https://github.com/pulp/pulp_deb/issues/797)

### Improved Documentation

-   Fixed infinite loading when searching for specific terms.
    [#765](https://github.com/pulp/pulp_deb/issues/765)

---

## 2.20.2 (2023-04-26) {: #2.20.2 }

### Bugfixes

-   Fixed a bug that prevented orphan cleanup due to protected foreign keys.
    [#690](https://github.com/pulp/pulp_deb/issues/690)

### Misc

-   Add precompiled test data for pytest to use in functional tests
    [#395](https://github.com/pulp/pulp_deb/issues/395)

---

## 2.20.1 (2022-12-07) {: #2.20.1 }

### Bugfixes

-   Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
    [#612](https://github.com/pulp/pulp_deb/issues/612)
-   Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
    or more releases.
    [#674](https://github.com/pulp/pulp_deb/issues/674)

---

## 2.20.0 (2022-10-19) {: #2.20.0 }

### Features

-   Added the option to synchronize repositories using an optimized mode (enabled by default).
    [#564](https://github.com/pulp/pulp_deb/issues/564)
-   Added feature to import/export pulp_deb content
    [#605](https://github.com/pulp/pulp_deb/issues/605)

### Bugfixes

-   Fixed handling of download URLs containing special characters in the path part.
    [#571](https://github.com/pulp/pulp_deb/issues/571)
-   Fixed several serializer bugs preventing the manual creation of structure content of type
    `ReleaseArchitecture`, `ReleaseComponent`, and `PackageReleaseComponent`.
    [#575](https://github.com/pulp/pulp_deb/issues/575)
-   Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
    [#601](https://github.com/pulp/pulp_deb/issues/601)
-   Added a better error message when users try to create a repository version containing duplicate APT distributions.
    [#603](https://github.com/pulp/pulp_deb/issues/603)
-   Fixed a bug preventing the synchronization of repos referencing a single package from multiple package indices.
    [#632](https://github.com/pulp/pulp_deb/issues/632)

### Improved Documentation

-   Added workflow docs on manually creating structured repos.
    [#586](https://github.com/pulp/pulp_deb/issues/586)
-   Added feature overview documentation for the new Import/Export feature.
    [#624](https://github.com/pulp/pulp_deb/issues/624)

### Misc

-   Add a proper local SigningService setup for tests using pytest.
    [#402](https://github.com/pulp/pulp_deb/issues/402)

---

## 2.19.3 (2022-12-07) {: #2.19.3 }

### Bugfixes

-   Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
    [#612](https://github.com/pulp/pulp_deb/issues/612)
-   Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
    or more releases.
    [#674](https://github.com/pulp/pulp_deb/issues/674)

---

## 2.19.2 (2022-10-18) {: #2.19.2 }

### Bugfixes

-   Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
    [#601](https://github.com/pulp/pulp_deb/issues/601)
-   Added a better error message when users try to create a repository version containing duplicate APT distributions.
    [#603](https://github.com/pulp/pulp_deb/issues/603)

### Improved Documentation

-   Added workflow docs on manually creating structured repos.
    [#586](https://github.com/pulp/pulp_deb/issues/586)

---

## 2.19.1 (2022-07-25) {: #2.19.1 }

### Bugfixes

-   Fixed handling of download URLs containing special characters in the path part.
    [#571](https://github.com/pulp/pulp_deb/issues/571)
-   Fixed several serializer bugs preventing the manual creation of structure content of type
    `ReleaseArchitecture`, `ReleaseComponent`, and `PackageReleaseComponent`.
    [#575](https://github.com/pulp/pulp_deb/issues/575)

---

## 2.19.0 (2022-06-23) {: #2.19.0 }

### Bugfixes

-   Added support for uploading zstd compressed packages.
    [#459](https://github.com/pulp/pulp_deb/issues/459)
-   Fixed a bug causing inconsistent verbatim publications in combination with rare circumstances and streamed syncs.
    [#549](https://github.com/pulp/pulp_deb/issues/549)

### Misc

-   Converted CharField to TextField for pulp_deb models.
    [#532](https://github.com/pulp/pulp_deb/issues/532)

---

## 2.18.3 (2022-12-07) {: #2.18.3 }

### Bugfixes

-   Fixed a bug where architecture "all" packages were missing when syncing Debian 11 style repositories.
    [#612](https://github.com/pulp/pulp_deb/issues/612)
-   Fixed a bug where packages were only showing up in one Packages index file if they belonged to two
    or more releases.
    [#674](https://github.com/pulp/pulp_deb/issues/674)

---

## 2.18.2 (2022-10-18) {: #2.18.2 }

### Bugfixes

-   Added a better error message when users try to create a repository version containing duplicate APT distributions.
    [#603](https://github.com/pulp/pulp_deb/issues/603)

---

## 2.18.1 (2022-08-16) {: #2.18.1 }

### Bugfixes

-   Fixed handling of download URLs containing special characters in the path part.
    [#571](https://github.com/pulp/pulp_deb/issues/571)
-   Fixed several serializer bugs preventing the manual creation of structure content of type
    `ReleaseArchitecture`, `ReleaseComponent`, and `PackageReleaseComponent`.
    [#575](https://github.com/pulp/pulp_deb/issues/575)
-   Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
    [#601](https://github.com/pulp/pulp_deb/issues/601)

---

## 2.18.0 (2022-04-21) {: #2.18.0 }

### Features

-   Added experimental advanced copy API with support for structured copying.
    [#396](https://github.com/pulp/pulp_deb/issues/396)

### Bugfixes

-   Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
    [#422](https://github.com/pulp/pulp_deb/issues/422)
-   Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
    You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
    [#443](https://github.com/pulp/pulp_deb/issues/443)

### Misc

-   Reworked the sync handling for upstream repos using `No-Support-for-Architecture-all: Packages` format.
    This was needed to avoid clashes with the new arch filtering introduced in [#422](https://github.com/pulp/pulp_deb/issues/422).
    [#456](https://github.com/pulp/pulp_deb/issues/456)

---

## 2.17.2 (2022-10-18) {: #2.17.2 }

### Bugfixes

-   Fixed handling of download URLs containing special characters in the path part.
    [#571](https://github.com/pulp/pulp_deb/issues/571)
-   Fixed several serializer bugs preventing the manual creation of structure content of type
    `ReleaseArchitecture`, `ReleaseComponent`, and `PackageReleaseComponent`.
    [#575](https://github.com/pulp/pulp_deb/issues/575)
-   Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
    [#601](https://github.com/pulp/pulp_deb/issues/601)
-   Added a better error message when users try to create a repository version containing duplicate APT distributions.
    [#603](https://github.com/pulp/pulp_deb/issues/603)

---

## 2.17.1 (2022-04-21) {: #2.17.1 }

### Bugfixes

-   Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
    [#422](https://github.com/pulp/pulp_deb/issues/422)
-   Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
    You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
    [#443](https://github.com/pulp/pulp_deb/issues/443)

### Misc

-   Reworked the sync handling for upstream repos using `No-Support-for-Architecture-all: Packages` format.
    This was needed to avoid clashes with the new arch filtering introduced in [#422](https://github.com/pulp/pulp_deb/issues/422).
    [#456](https://github.com/pulp/pulp_deb/issues/456)

---

## 2.17.0 (2022-01-11) {: #2.17.0 }

### Features

-   Users can now use the FORCE_IGNORE_MISSING_PACKAGE_INDICES setting to define the corresponding behaviour for all remotes.
    [#9555](https://pulp.plan.io/issues/9555)

### Bugfixes

-   Fixed mirrored metadata handling when creating a new repository version.
    [#8756](https://pulp.plan.io/issues/8756)
-   Fixed a bug causing package validation to fail, when the package paragraph contains keys without values.
    [#8770](https://pulp.plan.io/issues/8770)
-   Fixed a bug causing publications to reference any `AptReleaseSigningService` via a full URL instead of just a `pulp_href`.
    [#9563](https://pulp.plan.io/issues/9563)

---

## 2.16.3 (2022-10-18) {: #2.16.3 }

### Bugfixes

-   Fixed handling of download URLs containing special characters in the path part.
    [#571](https://github.com/pulp/pulp_deb/issues/571)
-   Fixed several serializer bugs preventing the manual creation of structure content of type
    `ReleaseArchitecture`, `ReleaseComponent`, and `PackageReleaseComponent`.
    [#575](https://github.com/pulp/pulp_deb/issues/575)
-   Added handling for the special case when publishing an upstream repo containing a distribution named "default" using both simple and structured publish modes.
    [#601](https://github.com/pulp/pulp_deb/issues/601)
-   Added a better error message when users try to create a repository version containing duplicate APT distributions.
    [#603](https://github.com/pulp/pulp_deb/issues/603)

---

## 2.16.2 (2022-04-21) {: #2.16.2 }

### Features

-   Users can now use the FORCE_IGNORE_MISSING_PACKAGE_INDICES setting to define the corresponding behaviour for all remotes.
    [#9555](https://github.com/pulp/pulp_deb/issues/9555)

### Bugfixes

-   Made the sync workflow robust with respect to upstream package indices containing packages with a wrong architecture.
    [#422](https://github.com/pulp/pulp_deb/issues/422)
-   Changed the release file publication behaviour of the APT publisher to prevent a design clash with apt-secure.
    You may set PUBLISH_RELEASE_FILE_LABEL and PUBLISH_RELEASE_FILE_VERSION to True to revert to the old behaviour.
    [#443](https://github.com/pulp/pulp_deb/issues/443)

### Misc

-   Reworked the sync handling for upstream repos using `No-Support-for-Architecture-all: Packages` format.
    This was needed to avoid clashes with the new arch filtering introduced in [#422](https://github.com/pulp/pulp_deb/issues/422).
    [#456](https://github.com/pulp/pulp_deb/issues/456)

---

## 2.16.1 (2022-01-13) {: #2.16.1 }

### Bugfixes

-   Fixed a bug causing package validation to fail, when the package paragraph contains keys without values.
    (backported from #8770)
    [#432](https://github.com/pulp/pulp_deb/issues/432)
-   Fixed a bug causing publications to reference any `AptReleaseSigningService` via a full URL instead of just a `pulp_href`.
    (backported from #9563)
    [#433](https://github.com/pulp/pulp_deb/issues/433)

---

## 2.16.0 (2021-10-28) {: #2.16.0 }

### Bugfixes

-   Flat repo syncs were made more robust with respect to minimal release files.
    [#7673](https://pulp.plan.io/issues/7673)
-   Fixed a bug causing syncs to fail if upstream repos have more than 256 characters worth of distributions, components, or architectures.
    [#9277](https://pulp.plan.io/issues/9277)
-   Added fix to delete package fields with values of an incorrect type.
    [#9333](https://pulp.plan.io/issues/9333)

### Misc

-   Amended dispatch arguments deprecated by pulpcore in anticipation of removal.
    [#9349](https://pulp.plan.io/issues/9349)

---

## 2.15.1 (2021-10-27) {: #2.15.1 }

### Misc

-   Amended dispatch arguments deprecated by pulpcore in anticipation of removal.
    (backported from #9349)
    [#9505](https://pulp.plan.io/issues/9505)

---

## 2.15.0 (2021-08-26) {: #2.15.0 }

### Features

-   Add custom_fields to hold non-standard PackageIndex fields
    [#8232](https://pulp.plan.io/issues/8232)

### Bugfixes

-   The plugins async pipeline was made Django 3 compatible in anticipation of pulpcore 3.15.
    [#9299](https://pulp.plan.io/issues/9299)

### Improved Documentation

-   Reworked the plugin installation docs to be helpful to new users.
    [#9186](https://pulp.plan.io/issues/9186)

### Misc

-   Added touch statements to prevent false positives during orphan cleanup.
    [#9162](https://pulp.plan.io/issues/9162)
-   Replaced deprecated JSONField model from contrib with the one available with Django 3.
    [#9300](https://pulp.plan.io/issues/9300)

---

## 2.14.1 (2021-07-29) {: #2.14.1 }

Compatible with: `pulpcore>=3.14,<3.16`

### Misc

-   Re-enabled Python 3.6 and 3.7 for the all 2.14.* releases.
    [#9164](https://pulp.plan.io/issues/9164)
-   Added touch statements to prevent false positives during orphan cleanup.
    (backported from #9162)
    [#9175](https://pulp.plan.io/issues/9175)

---

## YANKED 2.14.0 (2021-07-22) {: #2.14.0 }

Yank reason: Python 3.6 and 3.7 support was prematurely dropped, and the orphan cleanup changes fro pulpcore 3.15 compatibility are still missing.

!!! warning
    This version was released in a broken state and has been yanked from pypi.
    The issues are addressed in the 2.14.1 release.

### Bugfixes

-   Add missing "Size" field in publications
    [#8506](https://pulp.plan.io/issues/8506)
-   Fixed a bug where arch=all package indices were not being synced when filtering by architecture.
    [#8910](https://pulp.plan.io/issues/8910)

### Removals

-   Dropped support for Python 3.6 and 3.7. pulp_deb now supports Python 3.8+.
    [#9036](https://pulp.plan.io/issues/9036)

### Misc

-   If remotes specify components or architectures that do not exist in the synchronized Release file, a warning is now logged.
    [#6948](https://pulp.plan.io/issues/6948)

---

## 2.13.1 (2021-08-02) {: #2.13.1 }

Compatible with: `pulpcore>=3.12,<3.15`

### Bugfixes

-   Add missing "Size" field in publications
    (backported from #8506)
    [#9167](https://pulp.plan.io/issues/9167)

---

## 2.13.0 (2021-05-27) {: #2.13.0 }

Compatible with: `pulpcore>=3.12,<3.15`

### Bugfixes

-   Completely disabled translation file synchronization to prevent sync failures.
    [#8671](https://pulp.plan.io/issues/8671)
-   Fixed a bug where components from the remote were being ignored when specified as the plain component.
    [#8828](https://pulp.plan.io/issues/8828)

---

## 2.12.1 (2021-05-25) {: #2.12.1 }

Compatible with: `pulpcore>=3.12,<3.14`

### Bugfixes

-   Completely disabled translation file synchronization to prevent sync failures.
    (Backported from <https://pulp.plan.io/issues/8671>)
    [#8735](https://pulp.plan.io/issues/8735)

---

## 2.12.0 (2021-05-10) {: #2.12.0 }

Compatible with: `pulpcore>=3.12,<3.14`

### Features

-   APT repositories may now reference an APT remote, that will automatically be used for syncs.
    [#8520](https://pulp.plan.io/issues/8520)

### Bugfixes

-   Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
    [#8410](https://pulp.plan.io/issues/8410)

### Misc

-   Migrated to new Distribution model for pulpcore 3.13 compatibility.
    [#8682](https://pulp.plan.io/issues/8682)

---

## 2.11.2 (2021-05-25) {: #2.11.2 }

Compatible with: `pulpcore>=3.10,<3.13`

### Bugfixes

-   Completely disabled translation file synchronization to prevent sync failures.
    (Backported from <https://pulp.plan.io/issues/8671>)
    [#8736](https://pulp.plan.io/issues/8736)

---

## 2.11.1 (2021-04-14) {: #2.11.1 }

Compatible with: `pulpcore>=3.10,<3.13`

### Bugfixes

-   Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
    (Backported from <https://pulp.plan.io/issues/8410>)
    [#8556](https://pulp.plan.io/issues/8556)

---

## 2.11.0 (2021-03-30) {: #2.11.0 }

Compatible with: `pulpcore>=3.10,<3.13`

No significant changes.

---

## 2.10.2 (2021-05-25) {: #2.10.2 }

Compatible with: `pulpcore>=3.10,<3.12`

### Bugfixes

-   Completely disabled translation file synchronization to prevent sync failures.
    (Backported from <https://pulp.plan.io/issues/8671>)
    [#8737](https://pulp.plan.io/issues/8737)

---

## 2.10.1 (2021-04-14) {: #2.10.1 }

Compatible with: `pulpcore>=3.10,<3.12`

### Bugfixes

-   Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
    (Backported from <https://pulp.plan.io/issues/8410>)
    [#8558](https://pulp.plan.io/issues/8558)

---

## 2.10.0 (2021-03-17) {: #2.10.0 }

Compatible with: `pulpcore>=3.10,<3.12`

### Bugfixes

-   Ensured the plugin respects the ALLOWED_CONTENT_CHECKSUMS setting.
    [#8388](https://pulp.plan.io/issues/8388)

### Improved Documentation

-   The plugin documentation was moved from <https://pulp-deb.readthedocs.io/> to <https://docs.pulpproject.org/pulp_deb/>.
    [#8113](https://pulp.plan.io/issues/8113)
-   Added workflow documentation on checksum handling configuration.
    [#8388](https://pulp.plan.io/issues/8388)

### Removals

-   Update AptReleaseSigningService validation to respect new base class requirements.
    [#8307](https://pulp.plan.io/issues/8307)

---

## 2.9.3 (2021-11-16) {: #2.9.3 }

### Misc

-   Added an upper bound of `<0.1.42` to the `python-debian` dependency to prevent breakage against python `<3.7`.

---

## 2.9.2 (2021-05-25) {: #2.9.2 }

Compatible with: `pulpcore>=3.7,<3.11`

### Bugfixes

-   Completely disabled translation file synchronization to prevent sync failures.
    (Backported from <https://pulp.plan.io/issues/8671>)
    [#8738](https://pulp.plan.io/issues/8738)

---

## 2.9.1 (2021-04-14) {: #2.9.1 }

Compatible with: `pulpcore>=3.7,<3.11`

### Bugfixes

-   Fixed the relative paths for translation files, which were causing sync failures and missing translation files.
    (Backported from <https://pulp.plan.io/issues/8410>)
    [#8559](https://pulp.plan.io/issues/8559)

---

## 2.9.0 (2021-01-14) {: #2.9.0 }

Compatible with: `pulpcore>=3.7,<3.11`

---

## 2.8.0 (2020-11-23) {: #2.8.0 }

Compatible with: `pulpcore>=3.7,<3.10`

### Features

-   Added an `ignore_missing_package_indices` flag to remotes which users may set to allow the synchronization of repositories with missing declared package indices.
    [#7467](https://pulp.plan.io/issues/7467)
-   Added the capability to synchronize repositories using "flat repository format".
    [#7502](https://pulp.plan.io/issues/7502)
-   Added ability to handle upstream repositories without a "Codename" field.
    [#7886](https://pulp.plan.io/issues/7886)

---

## 2.7.0 (2020-09-29) {: #2.7.0 }

Compatible with: `pulpcore>=3.7,<3.9`

---

## 2.6.1 (2020-09-03) {: #2.6.1 }

### Misc

-   Dropped the beta status of the plugin. The plugin is now GA!
    [#6999](https://pulp.plan.io/issues/6999)

---

## 2.6.0b1 (2020-09-01)

### Features

-   Added handling of packages with the same name, version, and architecture, when saving a new repository version.
    [#6429](https://pulp.plan.io/issues/6429)
-   Both simple and structured publish now use separate `Architecture: all` package indecies only.
    [#6991](https://pulp.plan.io/issues/6991)

### Bugfixes

-   Optional version strings are now stripped from the sourcename before using it for package file paths.
    [#7153](https://pulp.plan.io/issues/7153)
-   Fixed several field names in the to deb822 translation dict.
    [#7190](https://pulp.plan.io/issues/7190)
-   `Section` and `Priority` are no longer required for package indecies.
    [#7236](https://pulp.plan.io/issues/7236)
-   Fixed content creation for fields containing more than 255 characters by using `TextField` instead of `CharField` for all package model fields.
    [#7257](https://pulp.plan.io/issues/7257)
-   Fixed a bug where component path prefixes were added to package index paths twice instead of once when using structured publish.
    [#7295](https://pulp.plan.io/issues/7295)

### Improved Documentation

-   Added a note on per repository package uniqueness constraints to the feature overview documentation.
    [#6429](https://pulp.plan.io/issues/6429)
-   Fixed several URLs pointing at various API documentation.
    [#6506](https://pulp.plan.io/issues/6506)
-   Reworked the workflow documentation and added flow charts.
    [#7148](https://pulp.plan.io/issues/7148)
-   Completely refactored the documentation source files.
    [#7211](https://pulp.plan.io/issues/7211)
-   Added a high level "feature overview" documentation.
    [#7318](https://pulp.plan.io/issues/7318)
-   Added meaningful endpoint descriptions to the REST API documentation.
    [#7355](https://pulp.plan.io/issues/7355)

### Misc

-   Added tests for repos with distribution paths that are not equal to the codename.
    [#6051](https://pulp.plan.io/issues/6051)
-   Added a long_description to the python package.
    [#6882](https://pulp.plan.io/issues/6882)
-   Added test to publish repository with package index files but no packages.
    [#7344](https://pulp.plan.io/issues/7344)

---

## 2.5.0b1 (2020-07-15)

### Features

-   Added additional metadata fields to published Release files.
    [#6907](https://pulp.plan.io/issues/6907)

### Bugfixes

-   Fixed a bug where some nullable fields for remotes could not be set to null via the API.
    [#6908](https://pulp.plan.io/issues/6908)
-   Fixed a bug where APT client was installing same patches again and again.
    [#6982](https://pulp.plan.io/issues/6982)

### Misc

-   Renamed some internal models to Apt.. to keep API consistent with other plugins.
    [#6897](https://pulp.plan.io/issues/6897)

---

## 2.4.0b1 (2020-06-17)

### Features

-   The "Date" field is now added to Release files during publish.
    [#6869](https://pulp.plan.io/issues/6869)

### Bugfixes

-   Fixed structured publishing of architecture 'all' type packages.
    [#6787](https://pulp.plan.io/issues/6787)
-   Fixed a bug where published Release files were using paths relative to the repo root, instead of relative to the release file.
    [#6876](https://pulp.plan.io/issues/6876)

---

## 2.3.0b1 (2020-04-29)

### Features

-   Added Release file signing using signing services.
    [#6171](https://pulp.plan.io/issues/6171)

### Bugfixes

-   Fixed synchronization of Release files without a Suite field.
    [#6050](https://pulp.plan.io/issues/6050)
-   Fixed publication creation with packages referenced from multiple package inecies.
    [#6383](https://pulp.plan.io/issues/6383)

### Improved Documentation

-   Documented bindings installation for the dev environment.
    [#6396](https://pulp.plan.io/issues/6396)

### Misc

-   Added tests for invalid Debian repositories (bad signature, missing package indecies).
    [#6052](https://pulp.plan.io/issues/6052)
-   Made tests use the bindings config from pulp-smash.
    [#6393](https://pulp.plan.io/issues/6393)

---

## 2.2.0b1 (2020-03-03)

### Features

-   Structured publishing (with releases and components) has been implemented.
    [#6029](https://pulp.plan.io/issues/6029)
-   Verification of upstream signed metadata has been implemented.
    [#6170](https://pulp.plan.io/issues/6170)

---

## 2.0.0b4 (2020-01-14)

No significant changes.

---

## 2.0.0b3 (2019-11-14)

### Features

-   Change relative_path from CharField to TextField
    [#4544](https://pulp.plan.io/issues/4544)
-   Add more validation for uploading packages and installer packages.
    [#5377](https://pulp.plan.io/issues/5377)

### Deprecations and Removals

-   Change _id, _created, _last_updated, _href to pulp_id, pulp_created, pulp_last_updated, pulp_href
    [#5457](https://pulp.plan.io/issues/5457)

-   Remove "_" from _versions_href, _latest_version_href
    [#5548](https://pulp.plan.io/issues/5548)

-   Removing base field: _type .
    [#5550](https://pulp.plan.io/issues/5550)

-   Sync is no longer available at the {remote_href}/sync/ repository={repo_href} endpoint. Instead, use POST {repo_href}/sync/ remote={remote_href}.

    Creating / listing / editing / deleting deb repositories is now performed on /pulp/api/v3/repositories/deb/apt/ instead of /pulp/api/v3/repositories/.
    [#5698](https://pulp.plan.io/issues/5698)

### Bugfixes

-   Fix fields filter.
    [#5543](https://pulp.plan.io/issues/5543)

### Misc

-   Depend on pulpcore, directly, instead of pulpcore-plugin.
    [#5580](https://pulp.plan.io/issues/5580)

---

## 2.0.0b2 (2019-10-02)

### Features

-   Rework Package and InstallerPackage serializers to allow creation from artifact or uploaded file with specifying any metadata.
    [#5379](https://pulp.plan.io/issues/5379)
-   Change generic content serializer to create content units by either specifying an artifact or uploading a file.
    [#5403](https://pulp.plan.io/issues/5403),
    [#5487](https://pulp.plan.io/issues/5487)

### Deprecations and Removals

-   Remove one shot uploader in favor of the combined create endpoint.
    [#5403](https://pulp.plan.io/issues/5403)

### Bugfixes

-   Change content serializers to use relative_path instead of _relative_path.
    [#5376](https://pulp.plan.io/issues/5376)

### Improved Documentation

-   Change the prefix of Pulp services from pulp-* to pulpcore-*
    [#4554](https://pulp.plan.io/issues/4554)
-   Reflect artifact and upload functionality in the content create endpoint documentation.
    [#5371](https://pulp.plan.io/issues/5371)

### Misc

-   PublishedMetadata is now a type of Content.
    [#5304](https://pulp.plan.io/issues/5304)
-   Replace ProgressBar with ProgressReport.
    [#5477](https://pulp.plan.io/issues/5477)

---

## 2.0.0b1 (2019-09-06)

### Features

-   Add oneshot upload functionality for deb type packages.
    [#5391](https://pulp.plan.io/issues/5391)

### Bugfixes

-   Add relative_path to package units natural key to fix uniqueness constraints.
    [#5377](https://pulp.plan.io/issues/5377)
-   Fix publishing of lazy content and add download_policy tests.
    [#5405](https://pulp.plan.io/issues/5405)

### Improved Documentation

-   Reference the fact you must have both _relative_path and relative_path.
    [#5376](https://pulp.plan.io/issues/5376)
-   Fix various documentation issues from API changes, plus other misc fixes.
    [#5380](https://pulp.plan.io/issues/5380)

### Misc

-   Adopting related names on models.
    [#4681](https://pulp.plan.io/issues/4681)
-   Generate and commit initial migrations.
    [#5401](https://pulp.plan.io/issues/5401)
