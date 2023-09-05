.. _upload_and_manage_content:

Package Uploads
================================================================================

.. include:: ../external_references.rst

.. figure:: upload.svg
   :alt: Sync repository with remote

   Next to synchronization, direct upload is the second way to obtain APT content for your Pulp instance.


Quickstart Example
--------------------------------------------------------------------------------

A working example for uploading a ``.deb`` package and hosting it in a ``pulp_deb`` repository:

.. code-block:: bash

   NAME='quickstart-upload-vim-amd64'
   pulp deb repository create --name=${NAME}
   wget ftp.de.debian.org/debian/pool/main/v/vim/vim_9.0.1378-2_amd64.deb
   pulp deb content upload --repository=${NAME} --file=vim_9.0.1378-2_amd64.deb
   pulp deb publication create --repository=${NAME}
   pulp deb distribution create --name=${NAME} --base-path=${NAME} --repository=${NAME}

By default a package uploaded directly to a repository like this will be placed in the ``upload`` component of the ``pulp`` distribution.
It follows we can configure our example repo in the ``/etc/apt/sources.list`` file on a consuming host as follows:

.. code-block:: bash

   deb http://<your_pulp_host>/pulp/content/quickstart-uploaded-vim-amd64/ pulp upload

.. note::
   You can think of the upload command as declarative and idempotent.
   In other words, you can upload the same package to your Pulp repository multiple times, and the task will succeed each time, but only the first time will result in any changes to your Pulp repository.

.. important::
   It is possible to have an uploaded package added to an arbitrary distribution-component combination, by supplying the ``distribution`` and ``component`` parameters to the package upload API endpoint.
   However, at the time of writing it is not possible to do this via Pulp CLI.
   It is also not possible to use Pulp CLI to create a release content in order to customize the release file fields.


Create a Structured Repo Manually
--------------------------------------------------------------------------------

To get around Pulp CLI limitations from the quickstart example, we present the following scripted example that uses ``http``  and ``jq`` to talk directly to the API.

.. note::
   You may also want to have a look at the `pulpcore upload documentation`_.

**Setup**

.. literalinclude:: ../_scripts/setup.sh
   :language: bash

**Workflow**

.. literalinclude:: ../_scripts/structured_repo.sh
   :language: bash

The final command from the sctipt should return a ``200 OK`` response.
