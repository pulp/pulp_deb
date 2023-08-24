Installation
================================================================================

.. include:: external_references.rst


As with all Pulp plugins, the installation method for ``pulp_deb`` depends on your chosen ``pulpcore`` installation method.
There are multiple `pulpcore installation options`_.
The default recommendation is to use the `Pulp container images`_, which are documented via the `Pulp container image documentation`_ and contain ``pulp_deb`` by default.

If you need more help with advanced installation scenarios you can either consult the documentation referenced above, or else join the ``pulp`` Matrix/IRC channel for interactive help.
See the `Pulp project help page`_ for more information and additional ways on how to get in contact with the Pulp community.


.. _pulp_cli_deb:

Setting up Pulp CLI for pulp_deb
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


.. _httpie_and_jq:

Setting up httpie and jq
--------------------------------------------------------------------------------

Where there are feature gaps in Pulp CLI, or for advanced scripting scenarios, it may be preferrable to interact with the :ref:`Pulp REST API <rest_api>` directly.
Examples within this documentation will use the `httpie`_ utility for this purpose.
httpie can be installed via ``pip``, so you could install it alongside Pulp CLI in a virtual python environment using:

.. code-block:: none

   pip install pulp-cli-deb httpie

You will need to configure your Pulp API credentials, or else specify them with each call to ``http``.
For example, you can adjust the following ``.netrc`` example as needed:

.. code-block:: none

   machine localhost
   login admin
   password password

For alternative methods, please consult ``http --help``.

Both in combination with Pulp CLI as well as httpie, we recommend and make use of `jq`_ for parsing API responses.
``jq`` can normally be installed via your preferred package manager, for example using ``sudo apt-get install jq`` for APT based systems.
Being a simple command-line JSON parser, ``jq`` requires no additional configuration.
