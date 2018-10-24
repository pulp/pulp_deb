.. _error-handling-basics:

Error Handling
--------------

Please see the [error-handling](https://docs.pulpproject.org/en/3.0/nightly/contributing/error-handling.html) section in the code guidelines.

Non fatal exceptions should be recorded with the
`~pulpcore.plugin.tasking.Task.append_non_fatal_error` method. These non-fatal exceptions
will be returned in a `~pulpcore.app.models.Task.non_fatal_errors` attribute on the resulting
`~pulpcore.app.models.Task` object.


