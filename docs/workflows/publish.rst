.. _publish:

Publish and Host
================================================================================

.. image:: publish.svg
   :alt: Publish content

This section assumes that you have a repository with content in it.
To do this, see the :doc:`sync` or :doc:`upload` documentation.


Create a Publication
--------------------------------------------------------------------------------

Creating a publication is based on a repository:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/repositories/deb/apt/

This will return a ``200 OK`` response:

.. code-block:: json

   {
       "count": 1,
       "next": null,
       "previous": null,
       "results": [
           {
               "description": null,
               "latest_version_href": "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/versions/1/",
               "name": "vim",
               "pulp_created": "2020-06-29T07:35:14.713025Z",
               "pulp_href": "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/",
               "versions_href": "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/versions/"
           }
       ]
   }

Publications contain extra settings for how to publish.
You can use the ``apt`` publisher on any repository of the apt type containing ``deb`` packages:

.. code-block:: bash

   http post $BASE_ADDR/pulp/api/v3/publications/deb/apt/ repository=/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/ simple=true

This will return a ``202 Accepted`` response:

.. code-block:: json

   {
       "task": "/pulp/api/v3/tasks/d49e056f-a637-454a-8797-67f81648b60f/"
   }

Depending on the size of your repository, this might take a while.
Check the status of the task by running the following command to see if the publication has been created:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/tasks/d49e056f-a637-454a-8797-67f81648b60f/

This will return a ``200 OK`` response:

.. code-block:: json

   {
       "child_tasks": [],
       "created_resources": [
           "/pulp/api/v3/publications/deb/apt/ecf87d05-978c-4327-8fe8-f50dc523b1a8/"
       ],
       "error": null,
       "finished_at": "2020-06-29T12:22:06.138655Z",
       "name": "pulp_deb.app.tasks.publishing.publish",
       "parent_task": null,
       "progress_reports": [],
       "pulp_created": "2020-06-29T12:22:05.892080Z",
       "pulp_href": "/pulp/api/v3/tasks/d49e056f-a637-454a-8797-67f81648b60f/",
       "reserved_resources_record": [
           "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/"
       ],
       "started_at": "2020-06-29T12:22:05.994098Z",
       "state": "completed",
       "task_group": null,
       "worker": "/pulp/api/v3/workers/6b8a7389-bafb-4d29-8e0b-184cd616ce10/"
   }

``state`` equaling ``completed`` indicates that your publication has been created successfully:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/tasks/d49e056f-a637-454a-8797-67f81648b60f/ | jq '.state'

This returns the path of the created publication:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/tasks/d49e056f-a637-454a-8797-67f81648b60f/ | jq '.created_resources[0]'


Create a Distribution
--------------------------------------------------------------------------------

View a publication that you want to distribute and make consumable:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/publications/deb/apt/ecf87d05-978c-4327-8fe8-f50dc523b1a8/

This will return a ``200 OK`` response:

.. code-block:: json

   {
       "pulp_created": "2020-06-29T12:22:06.006518Z",
       "pulp_href": "/pulp/api/v3/publications/deb/apt/ecf87d05-978c-4327-8fe8-f50dc523b1a8/",
       "repository": "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/",
       "repository_version": "/pulp/api/v3/repositories/deb/apt/250083a4-8eaa-42b6-a588-c48c2a2935f0/versions/1/",
       "signing_service": null,
       "simple": true,
       "structured": false
   }

To host a publication which makes it consumable by a package manager, users create a distribution which will serve the associated publication at ``/pulp/content/<distribution.base_path>``:

.. code-block:: bash

   http post $BASE_ADDR/pulp/api/v3/distributions/deb/apt/ name="nginx" base_path="nginx" publication=/pulp/api/v3/publications/deb/apt/ecf87d05-978c-4327-8fe8-f50dc523b1a8/

This will return a ``202 Accepted`` response:

.. code-block:: json

   {
       "task": "/pulp/api/v3/tasks/18159df8-b337-4ae8-b8cf-7ad0fba44bc7/"
   }

Viewing the task will indicate if the distribution has been successful:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/tasks/18159df8-b337-4ae8-b8cf-7ad0fba44bc7/

This will return a ``200 OK`` response:

.. code-block:: json

   {
       "child_tasks": [],
       "created_resources": [
           "/pulp/api/v3/distributions/deb/apt/5cde2b30-7d35-4d64-a46b-0a4e5c984359/"
       ],
       "error": null,
       "finished_at": "2020-06-29T12:26:39.815218Z",
       "name": "pulpcore.app.tasks.base.general_create",
       "parent_task": null,
       "progress_reports": [],
       "pulp_created": "2020-06-29T12:26:39.575822Z",
       "pulp_href": "/pulp/api/v3/tasks/18159df8-b337-4ae8-b8cf-7ad0fba44bc7/",
       "reserved_resources_record": [
           "/api/v3/distributions/"
       ],
       "started_at": "2020-06-29T12:26:39.683538Z",
       "state": "completed",
       "task_group": null,
       "worker": "/pulp/api/v3/workers/50a13e76-fe27-4e3e-8cee-ae5ec41d272a/"
   }

View the created resource (``created_resources``) to find the URL to the new repository hosted by Pulp:

.. code-block:: bash

   http get $BASE_ADDR/pulp/api/v3/distributions/deb/apt/5cde2b30-7d35-4d64-a46b-0a4e5c984359/

This will return a ``200 OK`` response:

.. code-block:: json

   {
       "base_path": "nginx",
       "base_url": "http://pulp3-source-debian10.hostname.example.com/pulp/content/nginx/",
       "content_guard": null,
       "name": "nginx",
       "publication": "/pulp/api/v3/publications/deb/apt/ecf87d05-978c-4327-8fe8-f50dc523b1a8/",
       "pulp_created": "2020-06-29T12:26:39.806283Z",
       "pulp_href": "/pulp/api/v3/distributions/deb/apt/5cde2b30-7d35-4d64-a46b-0a4e5c984359/"
   }

Running the following command will prove that Pulp exposes the repository as you'd expect:

.. code-block:: bash

   http get http://pulp3-source-debian10.hostname.example.com/pulp/content/nginx/

This returns a ``200 OK`` response:

.. code-block:: html

   <!DOCTYPE html>
           <html>
               <body>
                   <ul>
                       <li><a href="dists/">dists/</a></li>
                       <li><a href="pool/">pool/</a></li>
                   </ul>
               </body>
           </html>

You may use this url (``base_url``) to access Debian content from Pulp via a package manager like apt, i.e. in your ``/etc/apt/sources.list`` file.

An example apt source file could be like,

.. code-block:: ini

   deb [trusted=yes arch=amd64 ] http://pulp3-source-debian10.hostname.example.com/pulp/content/nginx/ default  all
