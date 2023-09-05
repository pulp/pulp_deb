.. _workflows_sync:

Repository Synchronization
================================================================================

.. include:: ../external_references.rst

.. figure:: sync.svg
   :alt: Sync repository with remote

   Synchronization is one of two ways to obtain APT content for your Pulp instance.

Quickstart Example
--------------------------------------------------------------------------------

A working example for synchronizing and hosting Debian bookworm content from `nginx.org`_:

.. code-block:: bash

   NAME='quickstart-nginx-bookworm-amd64'
   REMOTE_OPTIONS=(
     --url=http://nginx.org/packages/debian/
     --distribution=bookworm
     --component=nginx
     --architecture=amd64
   )
   pulp deb remote create --name=${NAME} ${REMOTE_OPTIONS[@]}
   pulp deb repository create --name=${NAME} --remote=${NAME}
   pulp deb repository sync --name=${NAME}
   pulp deb publication create --repository=${NAME}
   pulp deb distribution create --name=${NAME} --base-path=${NAME} --repository=${NAME}

The final command above, will include the ``base_url`` parameter in its output.
The accompanying value will tell you where the Pulp content app serves your newly created repository.

To re-sync, re-publish and re-distribute a newer version of the upstream repository:

.. code-block:: bash

   pulp deb repository sync --name=${NAME}
   pulp deb publication create --repository=${NAME}

The distribution is automatically updated since it was created using the ``--repository`` flag.
This enables auto-distributing of the latest publication created from the repository.

To configure our example repo in the ``/etc/apt/sources.list`` file on a consuming host:

.. code-block:: bash

   deb http://<your_pulp_host>/pulp/content/quickstart-nginx-bookworm-amd64/ bookworm nginx


Variation 1: Maximum Flexibility
--------------------------------------------------------------------------------

This second example will trade in some convenience for increased flexibility:

.. code-block:: bash

   NAME='flexible-nginx-bookworm-amd64'
   pulp deb repository create --name=${NAME}
   pulp deb repository sync --name=${NAME} --remote=quickstart-nginx-bookworm-amd64
   PUB_HREF=$(pulp deb publication create --repository=${NAME} | jq -r '.pulp_href')
   pulp deb distribution create --name=${NAME} --base-path=${NAME} --publication=${PUB_HREF}

- The repository is created first, and not linked to any remote.
  As a result we can and must specify the remote for each sync, in this case re-using the remote from the previous example.
- Rather than linking our distribution to our repository to enable auto-distributing the publication is specified explicitly.
  To do so, the publication href is stored in a variable parsed from the API response via ``jq`` at creation time.
  This is necessary since publications have no name.

The re-sync, workflow for this example is significantly more complicated:

.. code-block:: bash

   pulp deb repository sync --name=${NAME} --remote=quickstart-nginx-bookworm-amd64
   PUB_HREF=$(pulp deb publication create --repository=${NAME} | jq -r '.pulp_href')
   pulp deb distribution update --name=${NAME} --publication=${PUB_HREF}

One advantage of updating the distribution manually like this, is increased control over the time when attached clients are served the new version.
For large repositories, the ``sync`` and ``publication create`` actions can take a long time to complete, while a distribution update is near instantaneous and could be scheduled to run at a precise time.


Important APT Remote Flags
--------------------------------------------------------------------------------

The above examples are designed so that they can be modified for synchronizing arbitrary upstream repositories, simply by modifying the ``REMOTE_OPTIONS``.
A remote describes the sync options for some upstream repository.
As a result, we will now describe how to set some important sync flags:

- ``--url`` (required): The URL to the remote repository root.
  The repository root folder can normally be identified by the presence of a ``dists/`` and a ``pool/`` folder.
  For example, if you open http://ftp.de.debian.org/debian/ in a browser, you will see these folders there.
- ``--distribution`` (required): The path between the ``dists/`` folder, and some ``Release``/``InRelease`` file that should be synchronized.
  For example, if you open http://ftp.de.debian.org/debian/dists/bullseye/ in a browser, you will find the release files there, so this distribution must be given as ``bullseye``.
  A single APT repository may host many different APT distributions, so the ``--distribution`` flag may be specified multiple times.
- ``--component``: An APT repo component to sync.
  The ``Release``/``InRelease`` file of every APT repo distribution includes a ``Components:`` field with a list of valid components for that distribution.
  For example, if you check the file at http://ftp.de.debian.org/debian/dists/bullseye/InRelease, it includes the line ``Components: main contrib non-free``, so ``main``, ``contrib``, and ``non-free`` would all be valid values for the ``--component`` flag.
  If you do not supply any components on a remote, then all that are available will be synchronized.
- ``--architecture``: A Debian machine architecture to sync.
  This flag works exactly like the ``--component`` flag, with the only difference that the relevant field in the ``Release``/``InRelease`` file is the ``Architectures:`` field.
  For example, if some ``Release`` file includes the line ``Architectures: all amd64 arm64 i386``, then ``amd64``, ``arm64``, ``i386`` are all good values for the ``--architecture`` flag.
  A architecture value of ``all`` has special meaning, and never has to be specified on your remote.

Putting all of this together in a single example, we could create the following remote:

.. code-block:: bash

   NAME='debian-bullseye-amd64'
   REMOTE_OPTIONS=(
     --url=http://ftp.de.debian.org/debian/
     --distribution=bullseye
     --component=main
     --component=contrib
     --architecture=amd64
     --architecture=nonsense
   )
   pulp deb remote create --name=${NAME} ${REMOTE_OPTIONS[@]}

- By having specified the components ``main`` and ``contrib``, we are excluding the ``non-free`` component from our sync.
- By specifying the architecture ``amd64`` we are synchronizing all packages with architecture ``amd64`` but also packages with architecture ``all`` which are always synchronized.
- By also specifying the non existent architecture ``nonsense`` we are not changing the sync result at all, since specifying architectures or components that do not exist for some distribution does not result in any errors (though it will log a warning).

You can list the full list of available remote creation options using ``pulp deb remote create --help``.


Best Practice Recommendations
--------------------------------------------------------------------------------

We recommend sticking to the following best practice recommendations:

- Once you sync a remote into a repository don't modify what is synced to that repository.
  Keep using the same remote for that repository, and don't modify the distributions, components, or architectures parameters on the remote.
  If you do want to change these values it is almost always best to create a new remote, and sync it to a new Pulp repository.
- Use a single ``--distribution`` per remote.
  While it is possible to set multiple distributions on a single remote, and sync them into a single Pulp repository, this can easily lead to huge confusing reposiotries with performance issues.
  On the flip side it is cheap to create one remote and one repository for each distribution you want to sync.
  If you want to sync a lot of distributions, from the same upstream repository, this can easily be scripted.
- For official Debian repositories, never use values like ``stable``, ``oldstable``, ``oldoldstable-updates``, etc. for the distribution.
  Always use Debian distribution names like ``bookworm`` or ``bookworm-updates`` instead.
  The reason is that ``stable``, ``oldstable``, or ``oldoldstable`` are symlinks, that might suddenly be redirected to an entirely different APT repo distribution when a new Debian version is released.
- Always consider explicitly setting any ``--architecture`` values you want.
  If you know you just need ``amd64``, syncing all the other architectures could cost you a multiple in sync times and storage requirements compared to just syncing ``amd64``.
  Unless you have hosts with multiarch environments, consider syncing just one architecture per Pulp repository (similarly to syncing just a single distribution).
- For official Debian and Ubuntu repositories you normally want all the components, so it is ok not to set any components explicitly (this is interpreted as sync all that are available).
  However, some third party repositories sometimes host a large number of components that you may not need, so you should set just the components you need in such cases.
- Use a naming scheme for your remotes, that reflects the above.
  For example ``nginx-bookworm-amd64`` is a good name using the structure ``<repo_name>-<distribution>-<architecture>``.


Flat Reposiotry Format Example
--------------------------------------------------------------------------------

``pulp_deb`` supports synchronization from repositories using the deprecated `flat repository format`_.

.. note::
   An APT repo using flat repository format does not have a ``dists/`` folder.
   Rather it is characterized by a single ``Release`` and/or ``InRelease`` file, with a single package index right next to it.
   Most commonly all metadata files and all packages are stored directly in the repository root.
   Hence, the name: "flat repo format".

The following workflow synchronizes an example flat APT repo:

.. code-block:: bash

   NAME='nvidia-cuda-flat-amd64'
   REMOTE_OPTIONS=(
     --url=http://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/
     --distribution=/
     --architecture=amd64
   )
   pulp deb remote create --name=${NAME} ${REMOTE_OPTIONS[@]}
   pulp deb repository create --name=${NAME} --remote=${NAME}
   pulp deb repository sync --name=${NAME}
   pulp deb publication create --repository=${NAME}
   pulp deb distribution create --name=${NAME} --base-path=${NAME} --repository=${NAME}

- For a flat repository, the specified distribution must always end with a ``/``, most commonly, it will just be a ``/``.
  Conversely, a distribution string provided for a repository not using flat repository format must not end with ``/``!
- You must not provide more than one distribution for a flat repository.
- Since flat repositories do not contain components, there is no reason to use the ``--component`` flag.
- You may still filter by architecture using the ``--architecture`` flag.

.. important::
   Even though you are synchronizing a flat repository, ``pulp_deb`` will convert it to a regular structured APT repository on the publish.
   A distribution of ``/`` will be converted into a single distribution named ``flat-repo``, which will contain a single component named ``flat-repo-component``.

To configure the above repo in the ``/etc/apt/sources.list`` file on a consuming host:

.. code-block:: bash

   deb http://<your_pulp_host>/pulp/content/nvidia-cuda-flat-amd64/ flat-repo flat-repo-component

This contrasts with how you would configure the upstream flat repository:

.. code-block:: bash

   deb http://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/ /


Debian Security Reposiotry Example
--------------------------------------------------------------------------------

The debian security repository up to the ``buster`` release, uses a rare variation on the standard APT repository structure, where the distribution includes a ``/`` in it.
It is possible to create a remote for this as follows:

.. code-block:: bash

   NAME='debian-security-buster-amd64'
   REMOTE_OPTIONS=(
     --url=http://security.debian.org/debian-security/
     --distribution=buster/updates
     --component=updates/contrib
     --component=non-free
     --architecture=amd64
   )
   pulp deb remote create --name=${NAME} ${REMOTE_OPTIONS[@]}

.. note::
   For the example distribution above, the Release file components are listed as:

   ``Components: updates/main updates/contrib updates/non-free``

   You may specify a component of ``updates/main`` as either ``updates/main`` or simply as ``main``, ``pulp_deb`` will understand either way.
   The example is chosen to demonstrate both versions, as a matter of best practice we recommend being consistent.


Synchronizing from Partial Mirrors
--------------------------------------------------------------------------------

By default, syncs will fail if the upstream repository is missing package indices that are present in its Release file.
This breaks synchronization from partial mirrors, and can be overriden by setting ``ignore_missing_package_indices=True`` on the remote.
Alternatively, use ``FORCE_IGNORE_MISSING_PACKAGE_INDICES=True`` in your Pulp configuration file, to force this behaviour for all syncs irrespective of the individual remotes.

.. note::
   Currently, the remote option ``ignore_missing_package_indices`` cannot be set using Pulp CLI.
