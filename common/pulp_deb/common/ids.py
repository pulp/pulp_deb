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

SUPPORTED_TYPES = set([TYPE_ID_DEB])
