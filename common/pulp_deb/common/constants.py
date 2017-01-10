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

SYNC_STEP = 'sync_step'
SYNC_STEP_METADATA = 'sync_step_metadata'
SYNC_STEP_DOWNLOAD = 'sync_step_download'
SYNC_STEP_SAVE = 'sync_step_save'
