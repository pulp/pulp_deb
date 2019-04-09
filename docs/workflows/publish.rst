Publish and Host
================

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Publisher
------------------

Publishers contain extra settings for how to publish. You can use a deb publisher on any
repository that contains deb content::

$ http POST $BASE_ADDR/pulp/api/v3/publishers/deb/default/ name=bar

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/repositories/foo/publishers/deb/default/1/",
        ...
    }


Publish a repository with a publisher
-------------------------------------

Use the remote object to kick off a publish task by specifying the repository version to publish.
Alternatively, you can specify repository, which will publish the latest version.

The result of a publish is a publication, which contains all the information needed for a external package manager
like ``pip`` or ``apt-get`` to use. Publications are not consumable until they are hosted by a distribution::

$ http POST $BASE_ADDR/pulp/api/v3/publishers/deb/default/1/publish/ repository=$BASE_ADDR/pulp/api/v3/repositories/1/

Response::

    [
        {
            "_href": "http://localhost:24817/pulp/api/v3/tasks/fd4cbecd-6c6a-4197-9cbe-4e45b0516309/",
            "task_id": "fd4cbecd-6c6a-4197-9cbe-4e45b0516309"
        }
    ]

Host a Publication (Create a Distribution)
--------------------------------------------

To host a publication, (which makes it consumable by a package manager), users create a distribution which
will serve the associated publication at ``/pulp/content/<distribution.base_path>``::

$ http POST $BASE_ADDR/pulp/api/v3/distributions/ name='baz' base_path='foo' publication=$BASE_ADDR/publications/1/

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/distributions/1/",
       ...
    }

