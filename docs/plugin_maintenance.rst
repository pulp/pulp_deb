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

The `Pulp plugin template`_ is used to collect changes relevant to all Pulp plugins.
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
For documentation on each parameter, see the `Pulp plugin template README`_.

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

The general release steps are maintained in the `pulpcore release guide`_ wiki article.
This article also includes clear hints how those steps should be interpreted for plugins.
The release process tends to experience some churn, so this guide should always be consulted as the most up to date, single source of truth.

The following subsections collect ``pulp_deb`` specific hints and details, that go beyond the pulpcore release guide.

.. note::
   The plugin is released to pypi.org as the `pulp_deb python package`_.
   In addition a new `pulp-deb-client package`_ and `pulp_deb_client Ruby Gem`_ will be released.
   Client packages based on the latest plugin ``main`` branch are also released daily.
   See the :ref:`plugin template <using_the_plugin_template>` and the ``template_config.yml`` file for more information on daily client releases.


Updating the Release Branch CI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is generally desirable to apply at least the latest GitHub actions :ref:`plugin template <using_the_plugin_template>` before *every* release.
This means applying the plugin template to the main branch, before new Y-release branches are created, and also applying it to existing release branches before performing Z-releases.
For the most part, the plugin template can be applied more or less blindly from its latest main branch.
However, around major pulpcore, or CI changes, or when applying the plugin template to very old release branches careful understanding and review is sometimes required.
The older the release branch, the more likely it is the ``template_config.yml`` on the branch needs to be adjusted before applying the template.

For cherry-picking backports the ``.ci/scripts/cherrypick.sh`` script is used locally.
This will also be updated by applying the GitHub actions plugin template.


The pulpcore Deprecation Cycle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pulpcore will introduce breaking changes to the plugin API over a cycle of two ``Y`` releases.
Affected functions will be deprecated in some ``Y`` release, but will only be removed with the next ``Y`` release after that.
As a result, if we are releasing for the pulpcore ``3.8`` release, it should be safe to declare an upper bound of strictly smaller than ``3.10`` (up to and including ``3.9.*``).
This presupposes that we have already removed any dependencies on any deprecations announced for pulpcore ``3.8``.
See `pulpcore plugin API deprecation policy`_ for more information.

The lower bound should be changed directly in the ``main`` branch whenever some change actually requires a newer pulpcore version.
Therefore it should not normally be necessary to raise this at release time (beyond what it already was in the ``main`` branch).


Release Steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Careful reading of the `pulpcore release guide`_ wiki article is currently the best way to perform up to date release steps.
If you find any mistakes in the wiki article, start a community discussion to suggest changes.

.. note::
   Performing a ``pulp_deb`` release requires permissions to run the relevant `pulp_deb GitHub actions pipelines`_.
   Closing the relevant `pulp_deb milestone`_ also requires permissions on the issue tracker.
   Backport cherry-picks can be prepared by anyone who can open a ``pulp_deb`` PR.

.. note::
   The release pipeline may run into trouble if issues are assigned to the wrong `pulp_deb milestone`_.
   In such cases it is always possible to remove the problematic association and re-run the release pipeline (which is designed to be idempotent).


.. _release_announcements:

Release Announcements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently, release announcements are posted as `Pulp community forum announcements`_.
The easiest thing to do is to copy and amend an existing announcement like this `example pulp_deb release announcement`_.

Also send an email to the `Pulp project mailing list`_ (not to be confused with the `Pulp project development mailing list`_), that simply references the community announcement as follows:

.. code-block:: none

   To: pulp-list@redhat.com
   Subject: pulp_deb 2.14.1 is generally available

   Please see the community release announcement for more information:
   https://github.com/pulp/community/discussions/71

   Kind regards,
   Quirin Pamp (quba42)
   Software Engineer, pulp_deb plugin maintainer, ATIX AG
