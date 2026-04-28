"""Models to represent APT repository metadata

This module contains Pulp content models that are used to represent APT repository metadata not used
to encode APT repository structure. In particular this includes any fields within an APT repository
'Release' file, appart from 'Components' and 'Architectures', which encode APT repository structure.
"""

from django.db import models

from pulpcore.plugin.models import Content

from pulp_deb.app.constants import NULL_VALUE


class Release(Content):
    """
    The "Release" content.

    This model represents a debian release.
    """

    TYPE = "release"

    codename = models.TextField()
    suite = models.TextField()
    distribution = models.TextField()
    version = models.TextField(default=NULL_VALUE)
    origin = models.TextField(default=NULL_VALUE)
    label = models.TextField(default=NULL_VALUE)
    description = models.TextField(default=NULL_VALUE)

    repo_key_fields = ("distribution",)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (
            ("codename", "suite", "distribution", "version", "origin", "label", "description"),
        )
