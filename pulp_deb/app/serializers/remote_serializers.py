from rest_framework.serializers import (
    BooleanField,
    CharField,
)
from pulpcore.plugin.serializers import (
    RemoteSerializer,
)

from pulp_deb.app.models import (
    DebRemote,
)


class DebRemoteSerializer(RemoteSerializer):
    """
    A Serializer for DebRemote.
    """

    distributions = CharField(
        help_text='Whitespace separated list of distributions to sync',
        required=True,
    )

    components = CharField(
        help_text='Whitespace separatet list of components to sync',
        required=False,
    )

    architectures = CharField(
        help_text='Whitespace separated list of architectures to sync',
        required=False,
    )

    sync_sources = BooleanField(
        help_text='Sync source packages',
        required=False,
    )

    sync_udebs = BooleanField(
        help_text='Sync installer packages',
        required=False,
    )

    sync_installer = BooleanField(
        help_text='Sync installer files',
        required=False,
    )

    class Meta:
        fields = RemoteSerializer.Meta.fields + (
            'distributions',
            'components',
            'architectures',
            'sync_sources',
            'sync_udebs',
            'sync_installer',
        )
        model = DebRemote
