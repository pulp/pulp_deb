Debian Support
==============

This is a currently NON FUNCTIONAL, experimental project for supporting Debian repositories within
Pulp.

What we have today
------------------

* Support for using the pulp-admin command line for creating a pulp_deb repository as well as running
a sync and publishing the results.
* The framework for the importer to sync data from a remote repository.
* The framework for the distributor to publish the repository.

For Importing/syncing information from the web see
`plugins/pulp_deb/plugins/importers/sync.py`

For publishing information to the web see
`plugins/pulp_deb/plugins/distributors/steps.py`
The PublishMetadataStep and PublishContentStep need to be filled in to write out the
repository to disk.

TODO 
----
* TODO - Implement the importer to download a repository and load the contents into Pulp
* TODO - Implement the distributor steps necessary to publish the repository information
