from gettext import gettext as _

from pulp.common.error_codes import Error


# Create a section for general validation errors (DEB1000 - DEB2999)
# Validation problems should be reported with a general PLP1000 error with a more specific
# error message nested inside of it.
DEB1001 = Error("DEB1001", _("Error downloading file %(file_name)s. The file size does not match "
                             "the size listed in the Packages file."), ['file_name'])
