"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import Content, ContentArtifact, Remote, Publisher

logger = getLogger(__name__)


class DebContent(Content):
    """
    The "deb" content type.

    Define fields you need for your new content type and
    specify uniqueness constraint to identify unit of this type.

    For example::

        field1 = models.TextField()
        field2 = models.IntegerField()
        field3 = models.CharField()

        class Meta:
            unique_together = (field1, field2)
    """

    TYPE = 'deb'


class DebPublisher(Publisher):
    """
    A Publisher for DebContent.

    Define any additional fields for your new publisher if needed.
    """

    TYPE = 'deb'


class DebRemote(Remote):
    """
    A Remote for DebContent.

    Define any additional fields for your new importer if needed.
    """

    TYPE = 'deb'
