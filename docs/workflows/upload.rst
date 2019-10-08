Upload and Manage Content
=========================

Create a repository
-------------------

If you don't already have a repository, create one::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/ name=foo

Response::

    {
        "pulp_href": "/pulp/api/v3/repositories/1/",
        ...
    }


Upload a file to Pulp
---------------------

Each artifact in Pulp represents a file. They can be created during sync or created manually by uploading a file::

    $ http --form POST $BASE_ADDR/pulp/api/v3/artifacts/ file@./foo_1.0-1_amd64.deb

Response::

    {
        "pulp_href": "/pulp/api/v3/artifacts/1/",
        ...
        "sha256": "7086dbfcff02666d54af8dd4e9ad5a803027c1326a6fcc1442674ba4780edb5a",
    }


Create content from an artifact
-------------------------------

Now that Pulp has the content, its time to make it into a unit of content::

    $ http POST $BASE_ADDR/pulp/api/v3/content/deb/packages/ _artifact=/pulp/api/v3/artifacts/1/ relative_path=foo_1.0-1_amd64.deb

Response::

    {
        "pulp_href": "/pulp/api/v3/content/deb/packages/1/",
        "artifact": "/pulp/api/v3/artifacts/1/",
        "digest": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
        "filename": "my-content",
        "architecture": "amd64",
        "package_name": "foo",
        "description": "the best foo",
        "version": "1.0-1",
        "sha256": "7086dbfcff02666d54af8dd4e9ad5a803027c1326a6fcc1442674ba4780edb5a",
        "maintainer": "me@sample.com",
        "relative_path": "foo_1.0-1_amd64.deb",
        ...
    }

.. note:: If you do not specify `relative_path`, a common poll location will be generated.


Create content by uploading a file
----------------------------------

Instead of the two steps above, you can directly upload a file to the content create endpoint::

    $ http POST $BASE_ADDR/pulp/api/v3/content/deb/packages/ file@./foo_1.0-1_amd64.deb relative_path=foo_1.0-1_amd64.deb

Response::

    {
        "pulp_href": "/pulp/api/v3/content/deb/packages/1/",
        "artifact": "/pulp/api/v3/artifacts/1/",
        "digest": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
        "filename": "my-content",
        "architecture": "amd64",
        "package_name": "foo",
        "description": "the best foo",
        "version": "1.0-1",
        "sha256": "7086dbfcff02666d54af8dd4e9ad5a803027c1326a6fcc1442674ba4780edb5a",
        "maintainer": "me@sample.com",
        "relative_path": "foo_1.0-1_amd64.deb",
        ...
    }

.. note:: If you do not specify `relative_path`, a common poll location will be generated.


Add content to a repository
---------------------------

Once there is a content unit, it can be added to and removed from to repositories::

    $ http POST $BASE_ADDR/pulp/api/v3/repositories/1/versions/ add_content_units:="[\"http://localhost:24817/pulp/api/v3/content/deb/packages/1/\"]"
