TYPE_ID_IMPORTER = "deb_importer"
TYPE_ID_DISTRIBUTOR = "deb_distributor"

TYPE_ID_DEB = "deb"
UNIT_KEY_DEB = (
    "name", "version", "architecture", "checksumtype", "checksum")
EXTRA_FIELDS_DEB = set([
    'description', 'homepage', 'installed_size', 'maintainer',
    'multi_arch', 'original_maintainer', 'priority', 'section', 'source',
    # Dependency relationships
    'breaks', 'conflicts', 'depends', 'enhances', 'pre_depends',
    'provides', 'recommends', 'replaces', 'suggests'])

TYPE_ID_DEB_COMP = 'deb_component'
UNIT_KEY_DEB_COMP = (
    'name', 'distribution', 'repoid')
EXTRA_FIELDS_DEB_COMP = set([
    'packages'])

TYPE_ID_DEB_RELEASE = 'deb_release'
UNIT_KEY_DEB_RELEASE = (
    'distribution', 'repoid')

SUPPORTED_TYPES = set([TYPE_ID_DEB, TYPE_ID_DEB_COMP, TYPE_ID_DEB_RELEASE])
