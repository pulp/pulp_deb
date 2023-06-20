from gettext import gettext


class DuplicateDistributionException(Exception):
    """
    Exception to signal, that we are creating a repository versions containing multiple Release
    content with the same distribution.
    """

    def __init__(self, distribution, *args, **kwargs):
        message = gettext(
            "Cannot create the new repository version, since it contains multiple Release content "
            "with the same distribution '{}'.\n"
            "This known issue is tracked here: https://github.com/pulp/pulp_deb/issues/599\n"
            "You can check the issue for known workarounds. Please also consider posting what you "
            "did before getting this error, to help us to fix the underlying problem more quickly."
        ).format(distribution)
        super().__init__(message, *args, **kwargs)
