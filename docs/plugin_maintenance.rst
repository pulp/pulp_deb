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
   A ``X`` version release, is more of a high level communication, than something with a detailed technical definition.
   It is up to the judgement of plugin maintainers when a new ``X`` version is warranted.

A ``Y`` version release, signifies one or more of the following:

* This release contains new features.
* This release may require a newer version of pulpcore (or some other dependency) than the ``Y-1`` release branch did.
* A ``Y`` version release is given its own release branch.

A ``Z`` version release, signifies the following:

* A ``Z`` version release may contain only bugfixes (semantic versioning).
* A ``Z`` version change is cherry-picked to the relevant ``Y`` version release branch.

Pulp plugins follow a "release whenever" policy, this means both ``Y`` and ``Z`` releases may happen whenever there are relevant changes, and as the need arises.


Plugin Release Steps
--------------------------------------------------------------------------------

.. note::
   The `pulpcore release guide`_ wiki article is now badly out of date, but may still be of interest as a reference.

At the time of this writing the release process required the following steps:

#. (optional) Run the "CI Update" action and review and merge any resulting PRs.
#. (``Y`` version release only) Run the "Create New Release Branch" action.
#. Run the "Release Pipeline" action from the relevant release branch and merge any resulting PRs.
#. Check that each of the following has been released:
   * The `pulp_deb python package`_ on pypi.org.
   * The `pulp-deb-client package`_ on pypi.org.
   * The `pulp_deb_client Ruby Gem`_ on rubygems.org.
   * This ``pulp_deb`` documentation.
#. (``Y`` version release only) Update the ``ci_update_branches`` variable in the ``template_config.yml`` file in the `pulp_deb source repository`_.
#. (optional) Run the "changelog update" action to add any release branch changelog commits to the main branch.
   If you skip this, it will be picked up by the nightly CI.
#. Post a release announcement under `Pulp community forum announcements`_.
   Hint: Simply copy and past from past release announcements making adjustments as necessary.


.. _using_the_plugin_template:

Using the Plugin Template
--------------------------------------------------------------------------------

For existing plugins, the `Pulp plugin template`_ is used to keep the plugin CI up to date and synchronized across all plugins.
Applying the latest plugin template is primarily performed via GitHub actions pipeline.
This pipeline is periodically run or can be triggered manually (for example before a new ``Y`` release).
The pipeline will open a PR against every branch listed in the ``ci_update_branches`` variable of the ``template_config.yml`` file of the ``pulp_deb`` source repository.

It is also possible (and sometimes useful) to run the plugin template locally.
Make sure you clone the ``plugin_template`` repository in the same folder as the ``pulp_deb`` repository.
You can then issue the below template commands within the root of the plugin template repository to apply changes.

.. important::
   The following commands are usually applied via the GitHub actions pipeline, which is the preferred way for creating the needed PRs.

.. code-block:: none

   ./plugin-template --generate-config pulp_deb
   ./plugin-template --github pulp_deb

.. important::
   The following plugin template commands are primarily intended for creating the skeleton for a new plugin.
   It sometimes makes sense to apply them to an existing plugin, but the applied changes will clash with the existing plugin content, and need to be manually evaluated.

.. code-block:: none

   ./plugin-template --docs pulp_deb
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
