The ``pulp_deb`` Plugin
================================================================================

.. include:: external_references.rst

The ``pulp_deb`` plugin extends the `pulpcore python package`_ with the ability to host deb packages within APT repositories.
This plugin is a part of the `Pulp Project`_, and assumes some familiarity with the `pulpcore documentation`_.

If you are just getting started with the plugin, read the high level :ref:`feature overview <feature_overview>` first.
See :ref:`workflows <workflows>` for detailed usage examples.
See the :ref:`REST API <rest_api>` documentation for an exhaustive feature reference.

The examples in this documentation show examples in two formats: the `httpie` HTTP queries you would make to call the 
REST API itself, and (where implemented) a corresponding `pulp_cli_deb` pulp CLI equivalent. To read more about the
`pulp_cli_deb` command line plugin, read :ref:`pulp CLI plugin <pulp_cli_deb>`.

The most important places relating to this project:

* The `Pulp project`_ homepage.
* The `pulpcore documentation`_.
* The `pulp_deb issue tracker`_.
* The `pulp_deb source repository`_.
* The `pulp_deb python package`_.
* The `pulp-deb-client package`_ (contains API bindings for Python).
* The `pulp_deb_client Ruby Gem`_ (contains API bindings for Ruby).


Table of Contents
--------------------------------------------------------------------------------

.. toctree::
   :maxdepth: 1

   installation
   pulp_cli_deb
   feature_overview
   workflows
   rest_api
   bindings
   plugin_maintenance
   contributing
   changes
