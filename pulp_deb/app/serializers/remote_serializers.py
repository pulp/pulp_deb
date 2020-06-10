from rest_framework.serializers import BooleanField, CharField, ChoiceField

from pulpcore.plugin.models import Remote
from pulpcore.plugin.serializers import RemoteSerializer

from pulp_deb.app.models import AptRemote


class AptRemoteSerializer(RemoteSerializer):
    """
    A Serializer for AptRemote.
    """

    distributions = CharField(
        help_text="Whitespace separated list of distributions to sync", required=True,
    )

    components = CharField(
        help_text="Whitespace separatet list of components to sync", required=False,
    )

    architectures = CharField(
        help_text="Whitespace separated list of architectures to sync", required=False,
    )

    sync_sources = BooleanField(help_text="Sync source packages", required=False)

    sync_udebs = BooleanField(help_text="Sync installer packages", required=False)

    sync_installer = BooleanField(help_text="Sync installer files", required=False)

    gpgkey = CharField(
        help_text="Gpg public key to verify origin releases against", required=False,
    )

    policy = ChoiceField(
        help_text="The policy to use when downloading content. The possible values include: "
        "'immediate', 'on_demand', and 'streamed'. 'immediate' is the default.",
        choices=Remote.POLICY_CHOICES,
        default=Remote.IMMEDIATE,
    )

    class Meta:
        fields = RemoteSerializer.Meta.fields + (
            "distributions",
            "components",
            "architectures",
            "sync_sources",
            "sync_udebs",
            "sync_installer",
            "gpgkey",
        )
        model = AptRemote
