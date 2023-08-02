from rest_framework.serializers import BooleanField, ValidationError
from pulpcore.plugin.models import Publication
from pulpcore.plugin.serializers import (
    RelatedField,
    DistributionSerializer,
    PublicationSerializer,
    DetailRelatedField,
)

from pulp_deb.app.models import (
    AptDistribution,
    AptPublication,
    VerbatimPublication,
    AptReleaseSigningService,
)


class VerbatimPublicationSerializer(PublicationSerializer):
    """
    A Serializer for VerbatimPublication.
    """

    class Meta:
        fields = PublicationSerializer.Meta.fields
        model = VerbatimPublication


class AptPublicationSerializer(PublicationSerializer):
    """
    A Serializer for AptPublication.
    """

    simple = BooleanField(
        help_text="Activate simple publishing mode (all packages in one release component).",
        default=False,
    )
    structured = BooleanField(help_text="Activate structured publishing mode.", default=True)
    publish_upstream_release_fields = BooleanField(help_text="", required=False)
    signing_service = RelatedField(
        help_text="Sign Release files with this signing key",
        many=False,
        queryset=AptReleaseSigningService.objects.all(),
        view_name="signing-services-detail",
        required=False,
    )

    def validate(self, data):
        """
        Check that the publishing modes are compatible.
        """
        data = super().validate(data)
        if not data["simple"] and not data["structured"]:
            raise ValidationError("one of simple or structured publishing mode must be selected")
        return data

    class Meta:
        fields = PublicationSerializer.Meta.fields + (
            "simple",
            "structured",
            "signing_service",
            "publish_upstream_release_fields",
        )
        model = AptPublication


class AptDistributionSerializer(DistributionSerializer):
    """
    Serializer for AptDistributions.
    """

    publication = DetailRelatedField(
        required=False,
        help_text="Publication to be served",
        view_name_pattern=r"publications(-.*/.*)?-detail",
        queryset=Publication.objects.exclude(complete=False),
        allow_null=True,
    )

    class Meta:
        fields = DistributionSerializer.Meta.fields + ("publication",)
        model = AptDistribution
