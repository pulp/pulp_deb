Upload and Manage Content
=========================

Create a repository
-------------------

If you don't already have a repository, create one::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=foo

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/repositories/1/",
        ...
    }


Upload a file to Pulp
---------------------

Each artifact in Pulp represents a file. They can be created during sync or created manually by uploading a file::

    $ http --form POST $BASE_ADDR/pulp/api/v3/artifacts/ file@./my_content

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/artifacts/1/",
        ...
    }


Create content from an artifact
-------------------------------

Now that Pulp has the content, its time to make it into a unit of content.

    $ http POST $BASE_ADDR/pulp/api/v3/content/deb/packages/ _artifact=http://localhost:24817/pulp/api/v3/artifacts/1/ filename=my_content

Response::

    {
        "_href": "http://localhost:24817/pulp/api/v3/content/deb/packages/1/",
        "artifact": "http://localhost:24817/pulp/api/v3/artifacts/1/",
        "digest": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
        "filename": "my-content",
        "_type": "deb.packages"
    }

Add content to a repository
---------------------------

Once there is a content unit, it can be added and removed and from to repositories::

$ http POST $REPO_HREF/pulp/api/v3/repositories/1/versions/ add_content_units:="[\"http://localhost:24817/pulp/api/v3/content/deb/packages/1/\"]"
