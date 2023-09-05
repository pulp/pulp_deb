.. _workflows:

Workflows
================================================================================

This chapter includes usage examples for various workflows.
All examples will make use Pulp CLI, so make sure you have a working installation of :ref:`pulp-cli-deb <pulp_cli_deb>`.
Any workflows that cannot be achieved via Pulp CLI, will use ``httpie`` to talk to the :ref:`REST API <rest_api>` directly.

.. toctree::
   :maxdepth: 2

   workflows/sync
   workflows/upload
   workflows/publish
   workflows/signing_service
   workflows/advanced_copy
   workflows/checksums
