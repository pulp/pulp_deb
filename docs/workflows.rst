.. _workflows:

Workflows
================================================================================

This chapter assumes you have a working pulp :doc:`installation <../installation>` including the ``pulp_deb`` plugin.

.. include:: httpie_usage.rst

In order to make the workflows usable via copy and paste, we make use of environmental variables in all examples:

.. code-block:: bash

   export BASE_ADDR=http://<hostname>:24817

This chapter is structured into the following subsections:

.. toctree::
   :maxdepth: 2

   workflows/checksums
   workflows/sync
   workflows/upload
   workflows/publish
   workflows/structured_repo
