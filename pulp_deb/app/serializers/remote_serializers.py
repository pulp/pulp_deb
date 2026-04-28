from rest_framework.serializers import BooleanField, CharField, ChoiceField

from pulpcore.plugin.models import Remote
from pulpcore.plugin.serializers import RemoteSerializer

from pulp_deb.app.models import AptRemote


class AptRemoteSerializer(RemoteSerializer):
    """
    A Serializer for AptRemote.
    """

    distributions = CharField(
        help_text="Whitespace separated list of distributions to sync.\n"
        'The distribution is the path from the repository root to the "Release" '
        "file you want to access. This is often, but not always, equal to either "
        "the codename or the suite of the release you want to sync. If the "
        'repository you are trying to sync uses "flat repository format", the '
        'distribution must end with a "/". Based on "/etc/apt/sources.list" syntax.',
        required=True,
    )

    components = CharField(
        help_text="Whitespace separatet list of components to sync.\n"
        "If none are supplied, all that are available will be synchronized. "
        'Leave blank for repositores using "flat repository format".',
        required=False,
        allow_null=True,
    )

    architectures = CharField(
        help_text="Whitespace separated list of architectures to sync\n"
        "If none are supplied, all that are available will be synchronized. "
        "A list of valid architecture specification strings can be found by running "
        '"dpkg-architecture -L". A sync will download the intersection of the list '
        "of architectures provided via this field and those provided by the relevant "
        '"Release" file. Architecture="all" is always synchronized and does not need '
        "to be provided here.",
        required=False,
        allow_null=True,
    )

    sync_sources = BooleanField(help_text="Sync source packages", required=False)

    sync_udebs = BooleanField(help_text="Sync installer packages", required=False)

    sync_installer = BooleanField(help_text="Sync installer files", required=False)

    gpgkey = CharField(
        help_text="Gpg public key to verify origin releases against",
        required=False,
        allow_null=True,
    )

    ignore_missing_package_indices = BooleanField(
        help_text="By default, upstream repositories that declare architectures "
        "and corresponding package indices in their Release files without "
        "actually publishing them, will fail to synchronize.\n"
        'Set this flag to True to allow the synchronization of such "partial mirrors" '
        "instead.\n"
        "Alternatively, you could make your remote filter by architectures for "
        "which the upstream repository does have indices.",
        required=False,
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
            "ignore_missing_package_indices",
        )
        model = AptRemote
