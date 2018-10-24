Adding and Removing Content
===========================

Repositories have versions. A new immutable respository version is created when its set of content
units changes

To facilitate the creation of repository versions a
`pulpcore.plugin.models.RepositoryVersion` context manager is provided. Plugin Writers are
strongly encouraged to use RepositoryVersion as a context manager to provide transactional safety,
working directory setup, and database cleanup after encountering failures.

```
     with RepositoryVersion.create(repository) as new_version:

        # add content manually
        new_version.add_content(content)
        new_version.remove_content(content)
```

Synchronizing
-------------

A typical task to add and remove content to/from a repository is to synchronize with an external
source.

One of the ways to perform synchronization:

* Download and analyze repository metadata from a remote source.
* Decide what needs to be added to repository or removed from it.
* Associate already existing content to a repository by creating an instance of
  `~pulpcore.plugin.models.RepositoryContent` and saving it.
* Remove `~pulpcore.plugin.models.RepositoryContent` objects which were identified for
  removal.
* For every content which should be added to Pulp create but do not save yet:

  * instance of ``ExampleContent`` which will be later associated to a repository.
  * instance of `~pulpcore.plugin.models.ContentArtifact` to be able to create relations with
    the artifact models.
  * instance of `~pulpcore.plugin.models.RemoteArtifact` to store information about artifact
    from remote source and to make a relation with `~pulpcore.plugin.models.ContentArtifact`
    created before.

* If a remote content should be downloaded right away (aka ``immediate`` download policy), use
  the suggested  :ref:`downloading <download-docs>` solution. If content should be downloaded
  later (aka ``on_demand`` or ``background`` download policy), feel free to skip this step.
* Save all artifact and content data in one transaction:

  * in case of downloaded content, create an instance of
    `~pulpcore.plugin.models .Artifact`. Set the `file` field to the
    absolute path of the downloaded file. Pulp will move the file into place
    when the Artifact is saved. The Artifact refers to a downloaded file on a
    filesystem and contains calculated checksums for it.
  * in case of downloaded content, update the `~pulpcore.plugin.models.ContentArtifact` with
    a reference to the created `~pulpcore.plugin.models.Artifact`.
  * create and save an instance of the `~pulpcore.plugin.models.RepositoryContent` to
    associate the content to a repository.
  * save all created artifacts and content: ``ExampleContent``,
    `~pulpcore.plugin.models.ContentArtifact`,
    `~pulpcore.plugin.models.RemoteArtifact`.

* Use `~pulpcore.plugin.models.ProgressBar` to report the progress of some steps if needed.