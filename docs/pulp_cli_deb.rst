.. _pulp_cli_deb:

Pulp CLI plugin
================================================================================

Many of the examples in this documentation are based on the `httpie` command.
However, there is also a work-in-progress plugin for the `pulp-cli` command
line tool available.

To install the command line plugin, simply `pip install` it into the python
environment that your `pulp-cli` is installed into. This is most likely the
system pip if you have used the `pulp-installer` ansible based installation
method. In that case, you can install the CLI plugin like this:

.. code-block:: bash

    sudo pip3 install pulp_cli_deb

You can test if the plugin is installed by requesting help from pulp-cli, like
this:

.. code-block:: bash

    # pulp deb --help
    Usage: pulp deb [OPTIONS] COMMAND [ARGS]...

    Options:
    --help  Show this message and exit.

    Commands:
    distribution
    publication
    remote
    repository

We have endevoured to provide examples of using these commands where relevant in
the :ref:`workflows <workflows>` documentation.