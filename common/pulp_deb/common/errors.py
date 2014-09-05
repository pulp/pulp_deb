from gettext import gettext as _

from pulp.common.error_codes import Error


DEB0001 = Error('DEB0001',
                _('Create local repository at: %(path)s failed.  Reason: %(reason)s'),
                ['path', 'reason'])
