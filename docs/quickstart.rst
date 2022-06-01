Quickstart
================================================================================

.. include:: external_references.rst


If you want to have a quick introduction on how to use this plugin and mirror
an example remote, this is the right place.


Example for a mirror
--------------------------------------------------------------------------------

After you've added the CLI plugin, you can start by creating a repository:

.. code-block:: bash

   export name=test
   pulp deb repository create --name "${name}"

As an example remote we are going to add the nginx repository. Once the remote is added, you should
sync it directly. You can still sync it later if you want, therefore look a bit further down.
If you want to mirror only on demand (and have only the meta-data information available), use ``--no-mirror`` instead of ``--mirror``.

.. code-block:: bash

   pulp deb remote create --name "${name}" --url http://nginx.org/packages/debian --distribution buster
   pulp deb repository sync --name "${name}" --mirror --remote "${name}"

Once synced, you can create the publication (the metadata) and continue with creating a distribution to
make the content publicly available with a given base-path.

.. code-block:: bash

   pulp deb publication create --repository "${name}"
   pulp deb distribution create --name "${name}" --base-path "${name}" --repository "${name}"


Sync (again) AFTER distribution and publication
--------------------------------------------------------------------------------

If you need to sync after you have already distributed and published a repository,
use the following commands to do so. The autopublish feature like in ``pulp_rpm`` is not implemented (yet).
Though, auto-distributing is enabled already.

.. code-block:: bash

   pulp deb repository sync --name "${name}" --mirror --remote "${name}"
   pulp deb publication create --repository "${name}" --simple True

