.. _feature_overview:

Feature Overview
================================================================================

.. include:: external_references.rst

This chapter aims to give a high level overview of what features the plugin supports, including known limitations, so as to set realistic expectations on how the plugin can be used.

For detailed usage examples, see :ref:`workflows <workflows>` instead.
See the :ref:`REST API <rest_api>` documentation for an exhaustive feature reference.


Core Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. _repository_synchronization:

Repository Synchronization
--------------------------------------------------------------------------------

Synchronizing upstream repositories is one of two ways to obtain content for the ``pulp_deb`` plugin.
See :ref:`package uploads <package_uploads>` for the other.
The aim is for the plugin to be able to synchronize (and publish) arbitrary (valid) APT repositories.
This also includes repositories using `flat repository format`_.

When synchronizing an upstream repository, only content supported by the ``pulp_deb`` plugin is downloaded. This includes:

- ``Release``, ``InRelease``, and ``Release.gpg`` metadata files.
- Binary package indices, aka ``Packages`` files.
- Any ``.deb`` binary packages referenced by any package indices being synced.
- (optionally) Installer package indices, the associated ``.udeb`` installer packages, as well as some other installer file types.

Things that are not synchronized:

- Source indices and source packages.
- Language and translation files.
- Anything else not explicitly mentioned above.

If and how this synchronized content is ultimately used, is dependent on the publisher and its options.
For more information see :ref:`verbatim publishing <verbatim_publishing>` and :ref:`APT publishing <apt_publishing>` below.


.. _filtered_synchronization:

Filtered Synchronization
********************************************************************************

It is possible to synchronize only a subset of a given upstream repository by specifying a set of distributions (aka releases), components, and architectures to synchronize.
Specifying the desired distributions is mandatory, while not specifying any components or architectures is interpreted as: "synchronize all that are available".


Signature Verification
********************************************************************************

.. note::
   For APT repositories, only the ``Release`` file of each distribution is signed.
   This file contains various checksums for all other metadata files contained within the distribution, which in turn contain the checksums of the packages themselves.
   As a result, signing the ``Release`` file is sufficient to guarantee the integrity of the entire distribution.

You may provide your remotes with the relevant (public) GPG key for ``Release`` file signature verification.
When synchronizing an upstream repository using signature verification, any metadata files that cannot be verified are discarded.
If no relevant metadata files are left, a ``NoReleaseFile`` error is thrown and the sync fails.


.. _package_uploads:

Package Uploads
--------------------------------------------------------------------------------

Rather than synchronizing upstream repositories, it is also possible to upload ``.deb`` package files to the ``pulp_deb`` plugin in a variety of ways.
See the corresponding :ref:`workflow documentation <upload_and_manage_content>` for more information.
In general, uploading content works the same way as for any other Pulp plugin, so you may also wish to consult the `pulpcore upload documentation`_.


.. _apt_publishing:

Hosting APT Repositories
--------------------------------------------------------------------------------

Once you have obtained some content via synchronization, or upload, you will want to publish and distribute this content, so that your clients may consume your hosted APT repositories.

The default way to do so is to use the ``pulp_deb`` APT publisher.
This publisher will generate new metadata for any ``.deb`` packages stored in your Pulp repository.
Any upstream metadata, installer files, and installer packages will be ignored.
The APT publisher will publish all the distributions (aka releases), components, and architectures, that were synchronized to the Pulp repository being published (or else created during package upload).
It will also use a default ``pool/`` folder structure regardless of the package file locations used by the relevant upstream repository.

This approach guarantees a consistent set of packages and metadata is presented to your clients using the latest APT repository format specification.
It also allows you to sign the newly generated metadata using your own signing key.

An alternative is to use the ``pulp_deb`` :ref:`verbatim publisher <verbatim_publishing>`.


.. _metadata_signing:

Metadata Signing
********************************************************************************

The ``pulp_deb`` plugin allows you to sign any ``Release`` files generated by the APT publisher by providing it with a signing service of type ``AptReleaseSigningService`` at the time of creation.
It is also possible to use different signing services for different distributions within your APT repositories.


Advanced Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. _verbatim_publishing:

Verbatim Publishing
--------------------------------------------------------------------------------

.. note::
   Even though the interface is very different, the verbatim publisher is comparable to ``pulp_rpm``'s "full mirror" sync feature.

The verbatim publisher is an alternative to the ``pulp_deb`` plugin's main :ref:`APT publisher <apt_publishing>`.
It will recreate an exact copy of the subset of an upstream repo that was synchronized into Pulp.
In other words, every synchronized file, including the upstream metadata will use the exact same relative path it had in the upstream repository.

**Advantages:**

- Upstream ``Release`` file signatures are retained, so clients can verify using the same keys as for the upstream repository.
- No new metadata is generated, so the verbatim publisher is much faster than the APT publisher.
- The verbatim publisher is the only way to publish synchronized installer files and packages.

**Disadvantages:**

- Since it relies on upstream metadata, it only works for synced content.
- It is not possible to sign a verbatim publication using your own :ref:`signing services <metadata_signing>`.
- Since the upstream repo is mirrored exactly, any errors in the upstream repo are retained.
- In some cases the upstream metadata may be inconsistent with what was synced into Pulp.


.. _advanced_copy:

Advanced Copy
--------------------------------------------------------------------------------

The plugin provides an advanced copy feature for moving packages between repositories.
Using this feature, it is possible to specify a set of packages to be copied from one Pulp repository to another, without having to manually specify the structure content that tells Pulp what packages go into what release component.
That way, the repository version created in the target repository, can be meaningfully published using the :ref:`APT publisher <apt_publishing>`, without relying on the "simple publishing" workaround.

We are also planning to expand the advanced copy feature with a :ref:`dependency solving <dependency_solving>` mechanism in the future.


Roadmap and Experimental
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
  This section describe features that are either planned for the future, or exist only in an experimental state.
  These features may lack expected functionality, or break unexpectedly.
  The API may still change in non-backwards compatible ways.


.. _import_export:

Import/Export
--------------------------------------------------------------------------------

The pulp_deb plugin already implements the pulpcore Import/Export API.
However, the current implementation is in a very basic state, that is not functionally usable.

.. note::
   This feature is actively being worked on by the plugin maintainers.
   For the latest state see the `import export issue`_.

See also the `pulpcore import-export docs`_.


Source Packages
--------------------------------------------------------------------------------

There is a open community contribution to add source package support.

.. note::
   This feature is an advanced state of development, but still waiting for working test coverage.
   For more information see the `source package PR`_.


.. _installation_from_synced_content:

Installation from Synced Content
--------------------------------------------------------------------------------

It is currently possible to synchronize installer indices and packages and publish them using the :ref:`verbatim publisher <verbatim_publishing>`.
However, there is no actual test coverage for installing Debian or Ubuntu hosts from a so published repository using the debian-installer.
We have also received feedback that the feature is currently broken since ``pulp_deb`` currently lacks the ability to synchronize language and translation files which are needed for the debian-installer.

.. note::
   There is not yet any firm time table for when this might be worked on.
   The next step is to solve the `translation file issue`_.


.. _dependency_solving:

Dependency Solving
--------------------------------------------------------------------------------

It is planned to expand the :ref:`advanced copy <advanced_copy>` feature with a dependency solving mechanism analogous to the one provided by ``pulp_rpm``.
The idea is to make it possible to specify a list of packages and automatically copy them *and their entire dependency trees* into a target repo.

.. note::
   There is not yet any firm time table for when this might be worked on.
   See the `dependency solving issue`_ for any new developments.


Domain and RBAC (Multi-Tenancy)
--------------------------------------------------------------------------------

There have been multiple requests for this feature in ``pulp_deb``.

.. note::
   The plugin maintainers have no plans to implement this.
   If you are interested in contributing to the development of this feature, please get in touch with us via the `multi tenancy feature request`_.
