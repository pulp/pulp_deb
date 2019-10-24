Synchronize a Repository
========================

Users can populate their repositories with content from an external sources by syncing
their repository.

Create a Repository
-------------------

Start by creating a new repository named "foo"::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=foo

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/repositories/1/",
        ...
    }


Create a Remote
---------------

Creating a remote object informs Pulp about an external content source.

``$ http POST $BASE_ADDR/pulp/api/v3/remotes/deb/apt/ name='bar' url='http://some.url/somewhere/'``

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/remotes/deb/apt/1/",
        ...
    }


Sync repository foo with remote
-------------------------------

Use the remote object to kick off a synchronize task by specifying the repository to
sync with. You are telling pulp to fetch content from the remote and add to the repository::

    $ http POST $BASE_ADDR/pulp/api/v3/remotes/deb/apt/1/sync/' repository=http://localhost:24817/pulp/api/v3/repositories/1/

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
        "task_id": "3896447a-2799-4818-a3e5-df8552aeb903"
    }

You can follow the progress of the task with a GET request to the task href. Notice that when the
synchroinze task completes, it creates a new version, which is specified in ``created_resources``::

    $  http GET $BASE_ADDR/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/

Response::

    {
        "pulp_href": "http://localhost:24817/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
        "pulp_created": "2018-05-01T17:17:46.558997Z",
        "created_resources": [
            "http://localhost:24817/pulp/api/v3/repositories/593e2fa9-af64-4d4b-aa7b-7078c96f2443/versions/6/"
        ],
        "error": null,
        "finished_at": "2018-05-01T17:17:47.149123Z",
        "non_fatal_errors": [],
        "parent": null,
        "progress_reports": [
            {
                "done": 0,
                "message": "Add Content",
                "state": "completed",
                "suffix": "",
                "task": "http://localhost:24817/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
                "total": 0
            },
            {
                "done": 0,
                "message": "Remove Content",
                "state": "completed",
                "suffix": "",
                "task": "http://localhost:24817/pulp/api/v3/tasks/3896447a-2799-4818-a3e5-df8552aeb903/",
                "total": 0
            }
        ],
        "spawned_tasks": [],
        "started_at": "2018-05-01T17:17:46.644801Z",
        "state": "completed",
        "worker": "http://localhost:24817/pulp/api/v3/workers/eaffe1be-111a-421d-a127-0b8fa7077cf7/"
    }
