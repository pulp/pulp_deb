from rest_framework.serializers import BooleanField, ValidationError, HyperlinkedRelatedField
from pulpcore.plugin.serializers import (
    PublicationDistributionSerializer,
    PublicationSerializer,
    PublishSettingsSerializer,
)
from pulp_deb.app.models import (
    AptDistribution,
    AptPublication,
    VerbatimPublication,
    AptReleaseSigningService,
    AptPublishSettings,
)


class AptPublishSettingsSerializer(PublicationSerializer):
    """
    A Serializer for AptPublishSettings.
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
        fields = PublishSettingsSerializer.Meta.fields + ("simple", "structured", "signing_service")
        model = AptPublishSettings


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
        model = AptPublication


class AptDistributionSerializer(PublicationDistributionSerializer):
    """
    Serializer for AptDistributions.
    """

    class Meta:
        fields = PublicationDistributionSerializer.Meta.fields
        model = AptDistribution
