from gettext import gettext as _

from pulpcore.plugin.exceptions import PulpException


class NoReleaseFile(PulpException):
    """
    Raised when no Release file can be found at the expected URL.
    """

    error_code = "DEB0001"

    def __init__(self, url):
        super().__init__()
        self.url = url

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Could not find a Release file at '{url}', try checking the 'url' and "
            "'distributions' option on your remote"
        ).format(url=self.url)


class NoValidSignatureForKey(PulpException):
    """
    Raised when verification of a Release file with the provided GPG key fails.
    """

    error_code = "DEB0002"

    def __init__(self, url):
        super().__init__()
        self.url = url

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Unable to verify any Release files from '{url}' using the GPG key provided."
        ).format(url=self.url)


class NoPackageIndexFile(PulpException):
    """
    Raised when no suitable package index file can be found.
    """

    error_code = "DEB0003"

    def __init__(self, relative_dir):
        super().__init__()
        self.relative_dir = relative_dir

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "No suitable package index files found in '{relative_dir}'. If you are syncing from "
            "a partial mirror, you can ignore this error for individual remotes "
            "(ignore_missing_package_indices='True') or system wide "
            "(FORCE_IGNORE_MISSING_PACKAGE_INDICES setting)."
        ).format(relative_dir=self.relative_dir)


class MissingReleaseFileField(PulpException):
    """
    Raised when an upstream Release file is missing a required field.
    """

    error_code = "DEB0004"

    def __init__(self, distribution, field):
        super().__init__()
        self.distribution = distribution
        self.field = field

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "The release file for distribution '{distribution}' is missing "
            "the required field '{field}'."
        ).format(distribution=self.distribution, field=self.field)


class UnknownNoSupportForArchitectureAllValue(PulpException):
    """
    Exception Signifying that the Release file contains the 'No-Support-for-Architecture-all' field,
    but with a value other than 'Packages'. We interpret this as an error since this would likely
    signify some unknown repo format, that pulp_deb is more likely to get wrong than right!
    """

    error_code = "DEB0005"

    def __init__(self, release_file_path, unknown_value):
        super().__init__()
        self.release_file_path = release_file_path
        self.unknown_value = unknown_value

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "The Release file at '{release_file_path}' contains the "
            "'No-Support-for-Architecture-all' field, with unknown value '{unknown_value}'! "
            "pulp_deb currently only understands the value 'Packages' for this field, please "
            "open an issue at https://github.com/pulp/pulp_deb/issues specifying the remote "
            "you are attempting to sync, so that we can improve pulp_deb!"
        ).format(
            release_file_path=self.release_file_path,
            unknown_value=self.unknown_value,
        )


class DuplicateReleaseFile(PulpException):
    """
    Raised when multiple ReleaseFile objects exist where only one is expected.
    """

    error_code = "DEB0006"

    def __init__(self, count):
        super().__init__()
        self.count = count

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Previous ReleaseFile count: {count}. There should only be one."
        ).format(count=self.count)


class DuplicatePackageIndex(PulpException):
    """
    Raised when multiple PackageIndex objects exist where only one is expected.
    """

    error_code = "DEB0007"

    def __init__(self, count):
        super().__init__()
        self.count = count

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Previous PackageIndex count: {count}. There should only be one."
        ).format(count=self.count)


class SourceSyncNotSupported(PulpException):
    """
    Raised when attempting to sync source repositories, which is not yet implemented.
    """

    error_code = "DEB0008"

    def __str__(self):
        return f"[{self.error_code}] " + _("Syncing source repositories is not yet implemented.")


class DuplicatePackageChecksumError(PulpException):
    """
    Raised when newly added packages have the same name, version, and architecture
    but different checksums.
    """

    error_code = "DEB0009"

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Cannot create repository version since there are newly added packages with the "
            "same name, version, and architecture, but a different checksum. If the log level "
            "is DEBUG, you can find a list of affected packages in the Pulp log. You can often "
            "work around this issue by restricting syncs to only those distribution component "
            "combinations, that do not contain colliding duplicates!"
        )


class ReleaseComponentDoesNotExist(PulpException):
    """Raised when a scoped removal refers to repository structure that does not exist."""

    error_code = "DEB0010"

    def __init__(self, distribution, component):
        super().__init__()
        self.distribution = distribution
        self.component = component

    def __str__(self):
        return f"[{self.error_code}] " + _(
            "Component '{component}' in distribution '{distribution}' does not exist in the "
            "selected repository version."
        ).format(component=self.component, distribution=self.distribution)
