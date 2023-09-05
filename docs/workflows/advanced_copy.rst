Advanced Copy
================================================================================

You can copy packages between Pulp repositories, *along with all associated structure content* using the advanced copy API.

For example, let us first set up an example repository with some test content:

.. code-block:: bash

   NAME='advanced-copy-example'
   REMOTE_OPTIONS=(
     --url=https://fixtures.pulpproject.org/debian/
     --distribution=ragnarok
     --distribution=ginnungagap
     --architecture=ppc64
     --architecture=armeb
     --policy=on_demand
   )
   pulp deb remote create --name=${NAME} ${REMOTE_OPTIONS[@]}
   pulp deb repository create --name=${NAME}-src --remote=${NAME}
   pulp deb repository sync --name=${NAME}-src

Now let us copy just one package from this src repository to a different target repository using the advanced copy API:

.. code-block:: bash

   NAME='advanced-copy-example'
   PULP_URL='http://localhost:5001'
   SRC_VERSION_HREF=$(pulp deb repository show --name=${NAME}-src | jq -r '.latest_version_href')
   TARGET_REPO_HREF=$(pulp deb repository create --name=${NAME}-target | jq -r '.pulp_href')
   PACKAGE_HREF=$(
     pulp deb repository content --type=package list --repository=${NAME}-src \
     | jq -r '.[0].pulp_href'
   )
   echo "\
   [
     {
       \"source_repo_version\": \"${SRC_VERSION_HREF}\",
       \"dest_repo\": \"${TARGET_REPO_HREF}\",
       \"content\": [
         \"${PACKAGE_HREF}\"
       ]
     }
   ]" > copy_config.json
   http post ${PULP_URL}/pulp/api/v3/deb/copy/ config:=@copy_config.json

After the copy task has completed, check the new repository version to see we do not just have ``deb.package`` type content, but also structure content of type ``deb.package_release_component`` and others:

.. code-block:: bash

   pulp deb repository version show --repository=${NAME}-target

Our example ``copy_config.json`` from the above example might look like this:

.. code-block:: json

   [
     {
       "source_repo_version": "/pulp/api/v3/repositories/deb/apt/018a600b-06d1-71a8-ac7f-6275e8ed7fd7/versions/1/",
       "dest_repo": "/pulp/api/v3/repositories/deb/apt/018a600b-a719-75ea-b7b8-4916176496ba/",
       "content": [
         "/pulp/api/v3/content/deb/packages/018a2c87-43d7-7013-a40f-db1ca6e2f367/"
       ]
     }
   ]

This example could easily be extended with extra values in the ``"content"`` list to copy several packages at once.
