Publish
=======

Publish tasks generate publications.  A publication contains metadata and artifacts associated
with content contained within a RepositoryVersion.

Using a `~pulpcore.plugin.models.Publication` context manager is highly encouraged.  On
context exit, the complete attribute is set True provided that an exception has not been raised.
In the event an exception has been raised, the publication is deleted.

One of the ways to perform publishing:

* Find `~pulpcore.plugin.models.ContentArtifact` objects which should be published
* For each of them create and save instance of `~pulpcore.plugin.models.PublishedArtifact`
  which refers to `~pulpcore.plugin.models.ContentArtifact` and
  `~pulpcore.app.models.Publication` to which this artifact belongs.
* Generate and write to a disk repository metadata
* For each of the metadata objects create and save  instance of
  `~pulpcore.plugin.models.PublishedMetadata` which refers to a corresponding file and
  `~pulpcore.app.models.Publication` to which this metadata belongs.
* Use `~pulpcore.plugin.models.ProgressBar` to report progress of some steps if needed.