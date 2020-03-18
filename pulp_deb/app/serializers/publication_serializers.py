from rest_framework.serializers import BooleanField, ValidationError, HyperlinkedRelatedField
from pulpcore.plugin.serializers import PublicationDistributionSerializer, PublicationSerializer

from pulp_deb.app.models import (
    DebDistribution,
    DebPublication,
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


class DebPublicationSerializer(PublicationSerializer):
    """
    A Serializer for DebPublication.
    """

    simple = BooleanField(
        help_text="Activate simple publishing mode (all packages in one release component).",
        default=False,
    )
    structured = BooleanField(help_text="Activate structured publishing mode.", default=False)
    signing_service = HyperlinkedRelatedField(
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
        fields = PublicationSerializer.Meta.fields + ("simple", "structured", "signing_service")
        model = DebPublication


class DebDistributionSerializer(PublicationDistributionSerializer):
    """
    Serializer for DebDistributions.
    """

    class Meta:
        fields = PublicationDistributionSerializer.Meta.fields
        model = DebDistribution
