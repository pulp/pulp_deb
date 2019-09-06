User Setup
==========

All REST API examples below use `httpie <https://httpie.org/doc>`__ to
perform the requests.

.. code-block:: bash

    machine localhost
    login admin
    password admin

If you configured the ``admin`` user with a different password, adjust the configuration
accordingly. If you prefer to specify the username and password with each request, please see
``httpie`` documentation on how to do that.


Install ``pulpcore``
--------------------

Follow the `installation
instructions <docs.pulpproject.org/en/3.0/nightly/installation/instructions.html>`__
provided with pulpcore.

Install plugin
--------------

This document assumes that you have
`installed pulpcore <https://docs.pulpproject.org/en/3.0/nightly/installation/instructions.html>`_
into a the virtual environment ``pulpvenv``.

Users should install from **either** PyPI or source.

From Source
***********

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   cd pulp_deb # assuming you have `git clone`d here.
   pip install -e .
   django-admin runserver 24817

Make and Run Migrations
-----------------------

.. code-block:: bash

   django-admin makemigrations deb
   django-admin migrate deb


Run Services
------------

.. code-block:: bash

   sudo systemctl restart pulp-content-app
   sudo systemctl restart pulp-api
   sudo systemctl restart pulp-resource-manager
   sudo systemctl restart pulp-worker@1
   sudo systemctl restart pulp-worker@2
