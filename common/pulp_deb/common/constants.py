# -- progress states ----------------------------------------------------------

STATE_NOT_STARTED = 'NOT_STARTED'
STATE_RUNNING = 'IN_PROGRESS'
STATE_COMPLETE = 'FINISHED'
STATE_FAILED = 'FAILED'
STATE_SKIPPED = 'SKIPPED'

COMPLETE_STATES = (STATE_COMPLETE, STATE_FAILED, STATE_SKIPPED)

REPO_NOTE_PKG = 'deb-repo'
REPOS_TITLE = "Debian Repositories"

# Importer configuration key names
CONFIG_COPY_CHILDREN = 'copy_children'
CONFIG_MAX_SPEED = 'max_speed'
CONFIG_NUM_THREADS = 'num_threads'
CONFIG_NUM_THREADS_DEFAULT = 5
CONFIG_REMOVE_MISSING_UNITS = 'remove_missing_units'
CONFIG_REMOVE_MISSING_UNITS_DEFAULT = False
CONFIG_REQUIRE_SIGNATURE = 'require_signature'
CONFIG_ALLOWED_KEYS = 'allowed_keys'
CONFIG_KEYSERVER = 'keyserver'
CONFIG_KEYSERVER_DEFAULT = 'hkp://wwwkeys.pgp.net'

# Distributor configuration key names
CONFIG_SERVE_HTTP = 'serve_http'
CONFIG_SERVE_HTTPS = 'serve_https'

DEFAULT_SERVE_HTTP = False
DEFAULT_SERVE_HTTPS = True

# Copy operation config
CONFIG_RECURSIVE = 'recursive'
DISPLAY_UNITS_THRESHOLD = 100

PUBLISH_REPO_STEP = 'publish_repo'
PUBLISH_MODULES_STEP = "publish_modules"
PUBLISH_DEB_STEP = "publish_deb"
PUBLISH_DEB_RELEASE_STEP = "publish_deb_releases"
PUBLISH_DEB_COMP_STEP = "publish_deb_components"
PUBLISH_REPODATA = "publish_repodata"

PUBLISH_STEPS = (PUBLISH_REPO_STEP, PUBLISH_MODULES_STEP,
                 PUBLISH_DEB_STEP, PUBLISH_REPODATA)

REPO_NODE_PKG = 'deb-repo'

# Configuration constants for export distributors
PUBLISH_HTTP_KEYWORD = 'http'
PUBLISH_HTTPS_KEYWORD = 'https'
PUBLISH_RELATIVE_URL_KEYWORD = 'relative_url'
PUBLISH_GENERATE_LISTING_FILE_STEP = 'generate_listing_files'

HTTP_PUBLISH_DIR_KEYWORD = 'http_publish_dir'
HTTPS_PUBLISH_DIR_KEYWORD = 'https_publish_dir'
PUBLISH_DEFAULT_RELEASE_KEYWORD = 'publish_default_release'

SYNC_STEP = 'sync_step'
SYNC_STEP_RELEASE_DOWNLOAD = 'sync_step_release_download'
SYNC_STEP_RELEASE_PARSE = 'sync_step_release_parse'
SYNC_STEP_PACKAGES_DOWNLOAD = 'sync_step_packages_download'
SYNC_STEP_PACKAGES_PARSE = 'sync_step_packages_parse'
SYNC_STEP_UNITS_DOWNLOAD_REQUESTS = 'sync_step_unit_download_requests'
SYNC_STEP_UNITS_DOWNLOAD = 'sync_step_unit_download'
SYNC_STEP_SAVE = 'sync_step_save'
SYNC_STEP_SAVE_META = 'sync_step_save_meta'

GPG_CMD = "gpg_cmd"
GPG_KEY_ID = "gpg_key_id"
