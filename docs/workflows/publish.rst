Publish and Host
================

This section assumes that you have a repository with content in it. To do this, see the
:doc:`sync` or :doc:`upload` documentation.

Create a Publication
--------------------

Publiations contain extra settings for how to publish. You can use a deb publisher on any
repository that contains deb content::

    $ http POST $BASE_ADDR/pulp/api/v3/publication/deb/apt/ repository=/pulp/api/v3/repositories/deb/apt/<uuid> simple=true

Response::

    {
        "task": "/pulp/api/v3/tasks/<uuid>",
    }


Host a Publication (Create a Distribution)
------------------------------------------

To host a publication, (which makes it consumable by a package manager), users create a distribution which
will serve the associated publication at ``/pulp/content/<distribution.base_path>``::

    $ http POST $BASE_ADDR/pulp/api/v3/distributions/deb/apt/ name='baz' base_path='foo' publication=$BASE_ADDR/pulp/api/v3/publications/deb/apt/1/

Response::

    {
        "task": "/pulp/api/v3/tasks/<uuid>",
    }

