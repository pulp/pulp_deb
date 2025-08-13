from rest_framework import serializers

from pulpcore.plugin.serializers import AlternateContentSourceSerializer
from pulp_deb.app.models import AptAlternateContentSource


class AptAlternateContentSourceSerializer(AlternateContentSourceSerializer):
    """
    Serializer for APT alternate content source.
    """

    def validate_paths(self, paths):
        """For deb we don't support per-path ACS. Reject any attempt to set non-empty paths."""
        if paths:
            raise serializers.ValidationError(
                "The 'paths' field is not supported for deb Alternate Content Sources yet."
            )
        return paths

    class Meta:
        fields = AlternateContentSourceSerializer.Meta.fields
        model = AptAlternateContentSource
