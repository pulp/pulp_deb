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
Then you can issue the following commands within the root of the plugin template repository.

To generate an up to date ``template_config.yml`` file in the base of the ``pulp_deb`` repository, use:

.. code-block:: none

   ./plugin-template --generate-config pulp_deb

You can adjust the configuration in the ``template_config.yml`` file to affect the other plugin template commands.

In order to apply the latest Travis pipeline changes use:

.. code-block:: none

   ./plugin-template --travis pulp_deb

In order to apply a full plugin skeleton from the plugin template use:

.. code-block:: none

   ./plugin-template --bootstrap pulp_deb

.. note::
   Bootstrapping the plugin will revert many files in the ``pulp_deb`` plugin to a skeletal version.
   When using the ``--bootstrap`` option one must carefully select and commit only those changes one really wants.


Plugin Release Process
--------------------------------------------------------------------------------

This section is based on the `pulpcore release guide`_.
It may need to be amended to reflect changes in the release process for pulpcore.

.. note::
   The plugin is released to pypi.org as the `pulp_deb python package`_.
   In addition a new `pulp-deb-client package`_ and `pulp_deb_client Ruby Gem`_ will be released.
   Client packages based on the latest plugin master branch are also released daily.
   See the :ref:`plugin template <using_the_plugin_template>` and the ``template_config.yml`` file for more information on those independent releases.


Preparing the Release Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::
   The release process uses the release script at ``.travis/release.py``.
   Before performing a major release, it may be worth checking if the :ref:`plugin template <using_the_plugin_template>` has new changes for this script.

Creating a release uses the ``.travis/release.py`` python script.
Running this script locally, requires the python dependencies from ``.travis/release_requirements.txt``.

Since the script will be creating commits, you should run it somewhere with a configured Git identity (i.e. not from within a ``pulplift`` development box).
As a result, a local python virtual environment is recommended.
This can be created as follows:

.. code-block:: none

   mkvirtualenv -r .travis/release_requirements.txt pulp_release

You can then reenter this venv later using ``workon pulp_release``.


Release Steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   As one might expect, various release steps require merge/push rights on the ``pulp_deb`` repository.
   However, a lot of the preparation can be performed by opening the relevant PRs.

For a ``Y`` release, perform the following steps (the example assumes we are releasing version ``2.6.0``):

#. Ensure the ``2.6.0``  `pulp_deb milestone`_ exists and contains the correct issues.

   .. note::
      You can double check this one more time after step 2.
      The ``Releasing 2.6.0`` commit from step 2 provides a redmine query for all issues that should be in the milestone.

#. Run the following commands to generate the ``release_2.6.0`` branch (with commits):

   .. code-block:: none

      workon pulp_release
      python .travis/release.py minor --lower 3.6 --upper 3.7

   The ``--lower`` and ``--upper`` parameters give the pulpcore version range that the release should be compatible with.
   Currently, each release is pegged to exactly one pulpcore-``Y`` release.
   This is due to change with the pulpcore ``3.7`` release.

#. Create a PR for the ``release_2.6.0`` branch generated in step 2.
#. Review and merge the PR to ``master``.
#. Create and push the ``2.6`` release branch (with the ``Releasing 2.6.0`` commit checked out).
#. On the ``2.6`` release branch, manually bump the version from ``2.6.0`` to ``2.6.1.dev`` in ``.bumpversion.cfg``, ``pulp_deb/__init__.py``, and  ``setup.py``.
   The commit message should be ``Bump to 2.6.1.dev``.
   This is for the benefit of any future ``Z`` releases on this branch.
   Don't forget to push.
#. Trigger the release by creating and pushing the ``2.6.0`` release tag at the ``Releasing 2.6.0`` commit.
#. Check the `pulp_deb travis build page`_, the `pulp_deb python package`_, the `pulp-deb-client package`_, and the `pulp_deb_client Ruby Gem`_ to see if everything has released correctly.
#. Finally, send a release announcement to the ``pulp-list`` mailing list.
   See :ref:`release announcements <release_announcements>` for more information.

For a ``Z`` release, perform the following steps (the example assumes we are releasing version ``2.6.1``):

#. Ensure the ``2.6.1``  `pulp_deb milestone`_ exists and contains the correct issues.

   .. note::
      You can double check this one more time after step 2.
      The ``Releasing 2.6.1`` commit from step 2 provides a redmine query for all issues that should be in the milestone.

#. Run the following commands to generate the ``release_2.6.1`` branch (with commits):

   .. code-block:: none

      workon pulp_release
      python .travis/release.py patch --lower 3.6 --upper 3.7

   The ``--lower`` and ``--upper`` parameters give the pulpcore version range that the release should be compatible with.
   For the release script to do the right thing, they need to be provided, even if they should not change for the ``Z`` release.

#. Create a PR for the ``release_2.6.1`` branch generated in step 2.
   It needs to go into the ``2.6`` branch, not ``master``!
#. Review and merge the PR.
#. Switch back to ``master``, and ``git cherry-pick -x`` the ``Building changelog for 2.6.1`` commit from the ``2.6`` release branch.
   Push directly to master or create and merge a PR for it.
#. Trigger the release by creating and pushing the ``2.6.1`` release tag at the ``Releasing 2.6.1`` commit (on the ``2.6`` release branch).
#. Check the `pulp_deb travis build page`_, the `pulp_deb python package`_, the `pulp-deb-client package`_, and the `pulp_deb_client Ruby Gem`_ to see if everything has released correctly.
#. Finally, send a release announcement to the ``pulp-list`` mailing list.
   See :ref:`release announcements <release_announcements>` for more information.


.. _release_announcements:

Release Announcements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``pulp_deb`` releases are announced on the ``pulp-list`` mailing list.

Example announcement email:

.. code-block:: none

   To: pulp-list@redhat.com
   Subject: pulp_deb 2.6.1 released

   pulp_deb version 2.6.1 [0] has been released.

   Have a look at the release notes [1] for changes.
   This version of the plugin is compatible with pulpcore version 3.6 [2].
   You can check the known issues [3] (and open new ones).

   [0] https://pypi.org/project/pulp-deb/2.6.0/
   [1] https://pulp-deb.readthedocs.io/en/latest/changes.html#b1-2020-09-01
   [2] https://www.redhat.com/archives/pulp-list/2020-August/msg00008.html
   [3] https://pulp.plan.io/projects/pulp_deb/issues

   kind regards,
   Quirin Pamp (quba42)

Feel free to add additional highlights from the release.
