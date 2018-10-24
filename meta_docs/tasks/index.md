Define your Tasks
-----------------

Any action that can run for a long time should be an asynchronous task. Plugin writers do not need
to understand the internals of the pulpcore tasking system, workers automatically execute tasks from
RQ, including tasks deployed by plugins.


Reservations
************

The tasking system adds a concept called "reservations" which ensures that actions that act on the
same resources are not run at the same time. To ensure data correctness, any action that alters the
content of a repository (thus creating a new version) must be run asynchronously, locking on the
repository and any other models which cannot change during the action. For example, sync tasks must
be asynchronous and lock on the repository and the remote. Publish should lock on the repository
version being published as well as the publisher.

