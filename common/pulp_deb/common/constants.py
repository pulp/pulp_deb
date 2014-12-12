# Content
DEB_TYPE_ID = 'deb'


# Platform
CONTENT_DIR = '/var/lib/pulp/content/%s' % DEB_TYPE_ID
LINKS_DIR = 'links'
SHARED_STORAGE = '/var/lib/pulp/content/shared/%s' % DEB_TYPE_ID


# Notes
REPO_NOTE_DEB = 'DEB'


# Plugins
WEB_IMPORTER_TYPE_ID = 'deb_web_importer'
WEB_DISTRIBUTOR_TYPE_ID = 'deb_web_distributor'
CLI_WEB_DISTRIBUTOR_ID = 'deb_web_distributor_name_cli'


# Configuration
IMPORTER_CONFIG_KEY_BRANCHES = 'branches'
IMPORTER_CONFIG_FILE_PATH = 'server/plugins.conf.d/deb_importer.json'
DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY = 'deb_publish_directory'
DISTRIBUTOR_CONFIG_VALUE_PUBLISH_DIRECTORY = '/var/lib/pulp/published/deb'
DISTRIBUTOR_CONFIG_FILE_PATH = 'server/plugins.conf.d/deb_distributor.json'

UNIT_KEY_FIELDS = ["name", "version", "architecture", "filename"]

# Steps
IMPORT_STEP_MAIN = 'import_main'
IMPORT_STEP_METADATA = 'import_metadata'

PUBLISH_STEP_WEB_PUBLISHER = 'deb_publish_step_web'
PUBLISH_STEP_CONTENT = 'deb_publish_content'
PUBLISH_STEP_METADATA = 'deb_publish_metadata'
PUBLISH_STEP_OVER_HTTP = 'deb_publish_over_http'

SYNC_STEP_DOWNLOAD = 'sync_step_download'
SYNC_STEP_SAVE = 'sync_step_save'
