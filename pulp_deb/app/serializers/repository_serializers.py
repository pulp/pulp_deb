from pulpcore.plugin.serializers import RepositorySerializer

from pulp_deb.app.models import DebRepository


class DebRepositorySerializer(RepositorySerializer):
    """
    A Serializer for DebRepository.
    """

    class Meta:
        fields = RepositorySerializer.Meta.fields
        model = DebRepository
