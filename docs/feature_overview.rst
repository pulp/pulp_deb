.. _feature_overview:

Feature Overview
================================================================================

.. include:: external_references.rst

This chapter aims to give a high level overview of what features the plugin currently supports, as well as any known limitations.
The aim is to provide users with enough information to make informed decisions about how they may or may not want to use this plugin, as well as to set realistic expectations on what will and will not work.

For detailed usage examples, see :ref:`workflows <workflows>` instead.
See the :ref:`REST API <rest_api>` documentation for an exhaustive feature reference.


.. _content_types:

Content Types
--------------------------------------------------------------------------------

Whether they are obtained via :ref:`synchronization <repository_synchronization>` or :ref:`direct upload <package_uploads>`, the ``pulp_deb`` plugin knows several different content types that it stores in the Pulp database.

Since each content type has its own REST API endpoint, you can find detailed descriptions in the :ref:`pulp_deb REST API documentation <rest_api>`.
Content types may be associated with certain artifacts (aka files) or contain only metadata.
For example, every content unit of the ``Packages`` content type is associated with exactly one ``.deb`` package file.
In other words, each content unit of this type represents exactly one ``.deb`` package.

Currently, the plugin has dedicated content types for various types of metadata, as well as ``.deb`` (binary) packages, and ``.udeb`` installer packages.
However, the latter can currently only be used in conjunction with the :ref:`verbatim publisher <verbatim_publishing>`.


.. _repository_synchronization:

Repository Synchronization
--------------------------------------------------------------------------------

Synchronizing upstream repositories is one of two ways to obtain content for the ``pulp_deb`` plugin.
See :ref:`package uploads <package_uploads>` for the other.
The aim is for the plugin to be able to synchronize (and publish) arbitrary (valid) APT repositories.
This also includes repositories using `flat repository format`_.

When synchronizing an upstream repository, only :ref:`content types <content_types>` supported by the ``pulp_deb`` plugin are downloaded.
Source packages, for example, are currently unsupported.

Even if a particular content type is downloaded during synchronization, it depends on the publisher that is used (:ref:`verbatim <verbatim_publishing>` or :ref:`standard APT <simple_and_structured_publishing>` publisher), whether that content is actually served by the Pulp content app as part of the Pulp distribution being created.
For example, the plugin's APT publisher does not use the downloaded upstream metadata files, but rather generates its own.
As another example, ``.udeb`` installer packages are currently only supported by the verbatim publisher.


.. _filtered_synchronization:

Filtered Synchronization
********************************************************************************

Synchronization works via the use of so called *Pulp remotes*, which describe the upstream repository you intend to synchronize.
It is possible to synchronize only a subset of a given upstream repository by specifying a set of "distributions", "components", and "architectures" in the remote.
Specifying the desired distributions is mandatory, while not specifying any components or architectures is interpreted as: "synchronize all that are available".

.. note::
   There will not be any errors if you specify components or architectures that do not exist for a given upstream distribution.
   This allows you to filter for components and architectures that may not be present in all of the upstream distributions, but it may also lead to unexpected results.
   For example, if you have made a typo, your desired component and/or architecture will simply be missing from your Pulp repository, without any failures or warnings.


Signature Verification
********************************************************************************

You may provide your remotes with the relevant (public) GPG key for ``Release`` file verification.

.. note::
   For APT repositories, only the ``Release`` file of each distribution is signed.
   This file contains various checksums for all other metadata files contained within the distribution, which in turn contain the checksums of the packages themselves.
   As a result, signing the ``Release`` file is sufficient to guarantee the integrity of the entire distribution.

When synchronizing an upstream repository using a remote with GPG key, any ``Release`` (or ``InRelease``) files that do not have a valid signature are discarded.
If, for a given distribution, there is no ``Release`` file that can be successfully verified, a ``NoReleaseFile`` error is thrown and the sync fails.


.. _package_uploads:

Package Uploads
--------------------------------------------------------------------------------

Rather than synchronizing upstream repositories, it is also possible to upload ``.deb`` package files to the ``pulp_deb`` plugin in a variety of ways.
See the corresponding :ref:`workflow documentation <upload_and_manage_content>` for more information.
In general, uploading content works the same way as for any other Pulp plugin, so you may also wish to consult the `pulpcore upload documentation`_.

.. important::
   There is currently no way of associating an uploaded ``.deb`` package with an existing distribution or component.
   There is also no way of manually creating a distribution and component to associate it with in the first place.
   As a result, manually uploaded packages will only show up in your publications, if you are using the "simple" publisher.
   For more information, see :ref:`simple and structured publishing <simple_and_structured_publishing>` below.

.. note::
   As a matter of best practice, the existence of multiple Debian packages with the same name, version, and architecture (but different content/checksum) should be avoided.
   Since the existence of such packages may be beyond the control of the ``pulp_deb`` user, the plugin takes a maximally permissive approach:
   Users can upload arbitrary (valid) packages to the Pulp database, but they cannot add multiple colliding packages of the same type (``.deb`` or ``.udeb``), to a single Pulp repository version.
   If users attempt to add one or more packages to a Pulp repository, and there are collisions with packages from the previous repository version, then the older packages will automatically be removed.
   If there are still collisions in the new repository version, an error is thrown and the task will fail.
   (This latter case can only happen if users attempt to add several colliding packages in a single API call.)


.. _simple_and_structured_publishing:

Simple and Structured Publishing
--------------------------------------------------------------------------------

You can create an APT publication from your synchronized repositories or your uploaded packages, using the ``/pulp/api/v3/publications/deb/apt/`` :ref:`REST API <rest_api>` endpoint.
A publication must use ``simple`` or ``structured`` mode (or both).

The simple publisher will publish all packages associated with the pulp repository version you are using in a single APT distribution named ``default``, which will contain a single component named ``all``.
That is, the simple publisher will add a single ``Release`` file at ``dists/default/Release`` to your published repository.
There will be one package index for each architecture for which there are packages (in addition to ``dists/default/all/binary-all/Packages``, which will always be created, but may be empty).

.. important::
   The simple publisher is currently the only way to include manually uploaded packages in your distribution.
   Be sure to use ``simple=true`` if you have uploaded packages (as opposed to synchronized them) to your repository.

The structured publisher will publish all the distributions (aka releases), components, and architectures, that were synchronized to the Pulp repository being published.
These various distribution, component, and architecture combinations, will contain the same packages as the upstream originals.
However, unlike the :ref:`verbatim publisher <verbatim_publishing>`, the APT publisher will generate all new metadata files for the publication.
It will also use a default ``pool/`` folder structure regardless of the package file locations used by the upstream repositories.

.. important::
   Since synchronization is currently the only supported way to obtain the needed metadata content units, the structured publisher only makes sense if you have synchronized some upstream APT repository into your Pulp instance.

Finally, the APT publisher (both structured and simple mode) will never append ``Architecture: all`` type packages to any architecture specific package indices.
It will always publish dedicated ``binary-all`` package indices.
This behaviour is irrespective of how any upstream repositories might have handled such packages.


.. _metadata_signing:

Metadata Signing
********************************************************************************

The ``pulp_deb`` plugin allows you to sign the ``Release`` files created by the simple or structured publishers by providing your publication with a signing service of type ``AptReleaseSigningService`` at the time of creation.

.. important::
   We currently lack a workflow documentation for creating and using an ``AptReleaseSigningService``.
   Until we get around to writing one, you can use the following resources to help you get started:

   * The `pulpcore metadata signing docs`_ describe the process for creating an ``AsciiArmoredDetachedSigningService``, which is largely analagous to creating an ``AptReleaseSigningService``.
   * The `signing service setup script`_ used by the ``pulp_deb`` test suite.
   * The `signing service script example`_ used by the ``pulp_deb`` test suite.


.. _verbatim_publishing:

Verbatim Publishing
--------------------------------------------------------------------------------

In addition to the ``pulp_deb`` plugin's main :ref:`APT publisher <simple_and_structured_publishing>`, there is also the "verbatim" publisher using a seperate :ref:`REST API <rest_api>` endpoint at ``/pulp/api/v3/publications/deb/verbatim/``.

The verbatim publisher will recreate the synced subset of any upstream repositories exactly.
It could also be referred to as "mirror mode".
If you have used :ref:`filtered synchronization <filtered_synchronization>` to obtain your repository, this reduces the synced subset as one would expect.
The synced subset currently includes ``.deb`` packages, ``.udeb`` installer packages, any upstream ``Release`` files, package indices, installer file indices, as well as installer and translation files.

The verbatim publisher (in combination with synchronization of a suitable upstream repository) is currently the only way to create a Pulp APT repository that can be used to install hosts with the Debian installer.

All files included in the verbatim publication will retain the exact same checksum that they had in the upstream repository.
Any upstream ``Release`` file signatures are simply retained.
As a result, hosts consuming the Pulp distribution can use the same GPG keys for repository verification as if they were attached directly to the upstream repository you synchronized.
On the flip side, it is currently not possible to sign a verbatim publication with your own :ref:`signing services <metadata_signing>`.
