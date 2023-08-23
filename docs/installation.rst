Installation
================================================================================

.. include:: external_references.rst


As with all Pulp plugins, the installation method for ``pulp_deb`` depends on your chosen ``pulpcore`` installation method.
There are multiple `pulpcore installation options`_.
The default recommendation is to use the `Pulp container images`_, which are documented via the `Pulp container image documentation`_.

If you need more help with advanced installation scenarios you can either consult the documentation referenced above, or else join the ``pulp`` Matrix/IRC channel for interactive help.
See the `Pulp project help page`_ for more information and additional ways on how to get in contact with the Pulp community.


.. _pulp_cli_deb:

Installing Pulp CLI for pulp_deb
--------------------------------------------------------------------------------

.. hint::
   We recommend installing Pulp CLI in a virtual python environment.

Pulp CLI for ``pulp_deb`` can be installed via the `pulp-cli-deb python package`_, on any host that can reach the REST API of your Pulp instance:

.. code-block:: none

   pip install pulp-cli-deb

This will also pull in the `pulp-cli python package`_ as a dependency.
The ``pulp-cli`` package contains the core of Pulp CLI, as well as the subcommands for many other Pulp content plugins like ``pulp_file`` and ``pulp_rpm``.

Once you have installed Pulp CLI, you will need to configure it, so that it can talk to the REST API of your Pulp instance:

.. code-block:: none

   pulp config create --help  # List a description of available config options
   pulp config create -e  # Open a generated default config file for editing

Make sure you set the ``base_url``, the ``api_root`` and any API credentials.
The default location for the CLI config file is ``~/.config/pulp/cli.toml``.

To test if Pulp CLI can reach the Pulp API use:

.. code-block:: none

   pulp status

.. note::
   The status API endpoint does not require authentication, so this will work even if the configured API credentials are incorrect.

For more information see the `pulp-cli documentation`_.
To open bug reports or feature requests against ``pulp-cli-deb``, see the `pulp-cli-deb issue tracker`_.

To start using the CLI commands for ``pulp_deb``, consult:

.. code-block:: none

   pulp deb --help
