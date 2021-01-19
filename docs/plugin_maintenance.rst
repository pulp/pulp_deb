Plugin Maintenance
================================================================================

.. include:: external_references.rst

This part of the documentation is intended as an aid to current and future plugin maintainers.


Plugin Version Semantics
--------------------------------------------------------------------------------

Release version strings of the ``pulp_deb`` plugin use the following format: ``X.Y.Z<beta_tag?>``

A ``X`` version release, signifies one or more of the following:

* There are major new features.
* There has been a major overhaul of existing features.
* The plugin has entered a new stage of its development.
* The plugin is compatible with a new pulpcore ``X`` version.

.. note::
   A ``X`` version release, is more of a high level "marketing" communication, than something with a detailed technical definition.
   It is up to the judgement of plugin maintainers when a new ``X`` version is warranted.

A ``Y`` version release, signifies the following:

* The ``Y`` version is the same, as the pulpcore-``Y`` version that the release is for.
* A ``Y`` version release is given its own release branch.
* A ``Y`` version release may contain new features or any other type of change.
* A ``Y`` version release is generally performed when a new pulpcore ``Y`` version has been released.

A ``Z`` version release, signifies the following:

* A ``Z`` version release may contain only bugfixes (semantic versioning).
* ``Z`` stream changes are cherry-picked to the relevant ``Y`` version release branch.
* ``Z`` stream changes may be released as soon as they are ready, and as needs arise.


.. _using_the_plugin_template:

Using the Plugin Template
--------------------------------------------------------------------------------

The `pulp plugin template`_ is used to collect changes relevant to all Pulp plugins.
When there are new changes, the plugin template can then be used to automatically apply those changes to plugins that do not yet include them.

To use the plugin template, make sure you have cloned the Git repository to the same folder as the ``pulp_deb`` repository.
You can then issue the below template commands within the root of the plugin template repository to apply changes.

.. note::
   It is generally fine to check out the latest ``master`` branch of the plugin template to apply changes.
   Alternatively, use the latest tag the plugin template has received.
   It is a good idea to reference the point in the plugin template history used in any commit messages, so others can reproduce what was done.

.. important::
   Not all plugin template commands cleanly destinguish between things needed to bootstrap a new plugin and things that should be applied to existing plugins again and again.
   As a result it is essential to manually go through any changes applied by the template, and only committing those that actually make sense.
   Changes from the ``--generate-config`` and ``--github`` commands can mostly be committed in full (check for `master` versus `main` branch naming), while changes from the ``--docs`` and ``--bootstrap`` commands may overwrite a lot of existing plugin code, but may sometimes add useful changes.

--------------------------------------------------------------------------------

To generate an up to date ``template_config.yml`` file in the base of the ``pulp_deb`` repository, use:

.. code-block:: none

   ./plugin-template --generate-config pulp_deb

You can adjust this configuration to affect the other plugin template commands.
For documentation on each parameter, see the `pulp plugin template README`_.

--------------------------------------------------------------------------------

In order to apply the latest GitHub actions pipeline changes use:

.. code-block:: none

   ./plugin-template --github pulp_deb

--------------------------------------------------------------------------------

In order to apply the latest documentation changes from the template use:

.. code-block:: none

   ./plugin-template --docs pulp_deb

--------------------------------------------------------------------------------

In order to apply a full plugin skeleton from the plugin template use:

.. code-block:: none

   ./plugin-template --bootstrap pulp_deb


Building the docs and API docs
--------------------------------------------------------------------------------

The content for the `pulp_deb REST API documentation <restapi.html>`_ is extracted via API call to a running pulp instance.
It will contain various docstrings from the plugin code as deployed to that instance.
As a result, building the docs can only be done via the CI pipelines or a full fledged development environment.

This can be done within a ``pulp3-source-*`` vagrant box from the ``pulp_installer`` repository, that has the ``pulp_deb`` plugin installed.
Within such a box run the following commands:

.. code-block:: none

   cd /home/vagrant/devel/pulp_deb/docs/
   make html

You can now find the built documentation at ``docs/_build/html/index.html`` within your local ``pulp_deb`` repository.
You can also find the API doc contents within ``docs/_static/api.json``.

You can open the locally built documentation in a browser, but you will not be able to view the API docs, since those make use of an external service, that obviously has no access to your local build.


Plugin Release Process
--------------------------------------------------------------------------------

This section is based on the `pulpcore release guide`_.
It may need to be amended to reflect changes in the release process for pulpcore.

.. note::
   The plugin is released to pypi.org as the `pulp_deb python package`_.
   In addition a new `pulp-deb-client package`_ and `pulp_deb_client Ruby Gem`_ will be released.
   Client packages based on the latest plugin ``main`` branch are also released daily.
   See the :ref:`plugin template <using_the_plugin_template>` and the ``template_config.yml`` file for more information on those independent releases.

.. note::
   While a lot of the preparation can be performed without any privileged access (simply by opening PRs), some release steps require merge/push rights on the upstream ``pulp_deb`` repository.


Preparing the Release Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::
   The release process uses the release script at ``.ci/scripts/release.py``.
   Before performing a major release, it may be worth checking if the :ref:`plugin template <using_the_plugin_template>` has new changes for this script.

Creating a release uses the ``.ci/scripts/release.py`` python script.
Running this script locally, requires the python dependencies from ``.ci/scripts/release_requirements.txt``.

Since the script will be creating commits, you should run it somewhere with a configured Git identity (i.e. not from within a ``pulplift`` development box).
As a result, a local python virtual environment is recommended.
This can be created as follows:

.. code-block:: none

   mkvirtualenv -r .ci/scripts/release_requirements.txt pulp_release

You can then reenter this venv later using ``workon pulp_release``.


X and Y Release Steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a ``X`` or a ``Y`` release, perform the following steps (the example assumes we are releasing version ``2.8.0``, at a time when the latest pulpcore release is one of ``3.8.*``):

#. Ensure the ``2.8.0``  `pulp_deb milestone`_ exists and contains the correct issues.

   .. note::
      You can double check this one more time after step 2.
      The ``Releasing 2.8.0`` commit from step 2 provides a redmine query for all issues that should be in the milestone.

#. Run the following commands to generate the ``release_2.8.0`` branch (with commits):

   .. code-block:: none

      workon pulp_release
      python .ci/scripts/release.py minor --lower 3.7 --upper 3.10

   The ``--lower`` and ``--upper`` parameters give the pulpcore version range that the release should be compatible with.
   The example would result in a declared compatibility range of ``pulpcore>=3.7,<3.10``.
   That is, for pulpcore ``3.7.*``, ``3.8.*``, and ``3.9.*``.

   .. note::
      pulpcore will introduce breaking changes to the plugin API over a cycle of two ``Y`` releases.
      Affected functions will be deprecated in some ``Y`` release, but will only be removed with the next ``Y`` release after that.
      As a result, if we are releasing for the pulpcore ``3.8`` release, it should be safe to declare an upper bound of strictly smaller than ``3.10`` (up to and including ``3.9.*``).
      This presupposes that we have already removed any dependencies on any deprecations announced for pulpcore ``3.8``.
      See `pulpcore plugin API deprecation policy`_ for more information.

      The lower bound should be changed directly in the ``main`` branch whenever some change actually requires a newer pulpcore version.
      Therefore it should not normally be necessary to raise this at release time (beyond what it already was in the ``main`` branch).

#. Create a PR for the ``release_2.8.0`` branch generated in step 2.
#. Review and merge the PR to ``main`` (make sure the tests on ``main`` turn green post merge).
#. Create the ``2.8`` release branch (with the ``Releasing 2.8.0`` commit checked out).
   The branch needs to be pushed directly into the upstream repository.
#. On the ``2.8`` release branch, manually bump the version from ``2.8.0`` to ``2.8.1.dev`` in ``.bumpversion.cfg``, ``pulp_deb/__init__.py``, and  ``setup.py``.
   The commit message should be ``Bump to 2.8.1.dev``.
   This is for the benefit of any future ``Z`` releases on this branch.
   Don't forget to push (and make sure the tests turn green for the branch).
#. Trigger the release by creating and pushing the ``2.8.0`` release tag at the ``Releasing 2.8.0`` commit.
#. Check the `pulp_deb GitHub actions pipelines`_, the `pulp_deb python package`_, the `pulp-deb-client package`_, and the `pulp_deb_client Ruby Gem`_ to see if everything has released correctly.
   Also check the :ref:`changelog <changelog>` of this documentation to make sure it was also updated.
#. Finally, send a release announcement to the `Pulp project mailing list`_.
   See :ref:`release announcements <release_announcements>` below.
#. If needed, also update this release documentation post release.


Z Release Steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a ``Z`` release, perform the following steps (the example assumes we are releasing version ``2.8.1``):

#. Ensure the ``2.8.1``  `pulp_deb milestone`_ exists and contains the correct issues.

   .. note::
      You can double check this one more time after step 2.
      The ``Releasing 2.8.1`` commit from step 2 provides a redmine query for all issues that should be in the milestone.

#. Run the following commands to generate the ``release_2.8.1`` branch (with commits):

   .. code-block:: none

      workon pulp_release
      python .ci/scripts/release.py patch --lower 3.7 --upper 3.10

   The ``--lower`` and ``--upper`` parameters give the pulpcore version range that the release should be compatible with.
   For the release script to do the right thing, they need to be provided, even though they should not be changed for ``Z`` releases.

#. Create a PR for the ``release_2.8.1`` branch generated in step 2.
   It needs to go into the ``2.8`` branch, not ``main``!
#. Review and merge the PR.
#. Switch back to ``main``, and ``git cherry-pick -x`` the ``Building changelog for 2.8.1`` commit from the ``2.8`` release branch.
   Push directly to ``main`` or create and merge a PR for it.
#. Trigger the release by creating and pushing the ``2.8.1`` release tag at the ``Releasing 2.8.1`` commit (on the ``2.8`` release branch).
#. Check the `pulp_deb GitHub actions pipelines`_, the `pulp_deb python package`_, the `pulp-deb-client package`_, and the `pulp_deb_client Ruby Gem`_ to see if everything has released correctly.
   Also check the :ref:`changelog <changelog>` of this documentation to make sure it was also updated.
#. Finally, send a release announcement to the `Pulp project mailing list`_.
   See :ref:`release announcements <release_announcements>` below.
#. If needed, also update this release documentation post release.


.. _release_announcements:

Release Announcements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``pulp_deb`` releases are announced on the `Pulp project mailing list`_.
Not to be confused with the `Pulp project development mailing list`_.

Example announcement email:

.. code-block:: none

   To: pulp-list@redhat.com
   Subject: pulp_deb 2.8.0 is Generally Available

   pulp_deb version 2.8.0 [0] has been released.
   It is compatible with pulpcore 3.7, pulpcore 3.8 [1] and pulpcore 3.9 (not yet released).

   Have a look at the release notes [2] for changes.
   Highlight is the ability to synchronize APT repositories using "flat repository format",
   as well as repositories that do not publish the Codename field in their metadata.
   You can check the known issues [3] (and open new ones).

   The Python client package (contains Python API bindings) may be found here [4].
   The Ruby client gem (contains Ruby API bindings) may be found here [5].

   [0] https://pypi.org/project/pulp-deb/2.8.0/
   [1] https://www.redhat.com/archives/pulp-list/2020-November/msg00004.html
   [2] https://docs.pulpproject.org/pulp_deb/changes.html#id1
   [3] https://pulp.plan.io/projects/pulp_deb/issues
   [4] https://pypi.org/project/pulp-deb-client/2.8.0/
   [5] https://rubygems.org/gems/pulp_deb_client/versions/2.8.0/

   Kind regards,
   Quirin Pamp (quba42)
   Software Engineer, pulp_deb plugin maintainer, ATIX AG
