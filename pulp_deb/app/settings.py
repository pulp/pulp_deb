"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

FORBIDDEN_CHECKSUM_WARNINGS = True

# Defines which publishers should be used for autopublish (along with which options) for
# repositories with autopublish=True but no defined autopubish_modes.
DEFAULT_AUTOPUBLISH_MODES = "simple structured verbatim"
