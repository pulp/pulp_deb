Added the ``publish_upstream_release_fields`` field to the repository model.
To avoid a breaking change in publication behaviour, existing repositories are populated with the setting set to ``False``, while any newly created repostiroies will default to ``True``.
Whatever the value on the repository, it can be overriden when creating a new publication.
