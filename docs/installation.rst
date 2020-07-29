Installation
================================================================================

.. _pulpcore installation: https://docs.pulpproject.org/installation/index.html

.. include:: httpie_usage.rst


Install ``pulpcore``
--------------------------------------------------------------------------------

Please see the `pulpcore installation`_ instructions.


Install ``pulp_deb`` Plugin
--------------------------------------------------------------------------------

This document assumes that you have used the `pulpcore installation`_ to install pulpcore into a the virtual environment ``pulpvenv``.

Users should install from **either** PyPI or source.


From Source
********************************************************************************

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   cd pulp_deb
   pip install -e .
   django-admin runserver 24817


Make and Run Migrations
--------------------------------------------------------------------------------

.. code-block:: bash

   pulp-manager makemigrations pulp_deb
   pulp-manager migrate pulp_deb


Run Services
--------------------------------------------------------------------------------

.. code-block:: bash

   pulp-manager runserver
   gunicorn pulpcore.content:server --bind 'localhost:24816' --worker-class 'aiohttp.GunicornWebWorker' -w 2
   sudo systemctl restart pulpcore-resource-manager
   sudo systemctl restart pulpcore-worker@1
   sudo systemctl restart pulpcore-worker@2
