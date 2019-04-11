Workflows
=========

If you have not yet installed the deb plugins on your Pulp installation, please follow our
:doc:`../installation`. These documents will assume you have the environment installed and
ready to go.

The REST API examples here use `httpie <https://httpie.org/doc>`_ to perform the requests.
The ``httpie`` commands below assume that the user executing the commands has a ``.netrc`` file
in the home directory. The ``.netrc`` should have the following configuration:

.. code-block:: bash

    machine localhost
    login admin
    password admin

If you configured the ``admin`` user with a different password, adjust the configuration
accordingly. If you prefer to specify the username and password with each request, please see
``httpie`` documentation on how to do that.

To make these workflows copy/pastable, we make use of environment variables. The first variable to
set is the hostname and port::

   $ export BASE_ADDR=http://<hostname>:24817


.. toctree::
   :maxdepth: 2

   sync
   upload
   publish-host
