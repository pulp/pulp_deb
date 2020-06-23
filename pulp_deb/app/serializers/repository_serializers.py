from pulpcore.plugin.serializers import RepositorySerializer

from pulp_deb.app.models import AptRepository


class AptRepositorySerializer(RepositorySerializer):
    """
    A Serializer for AptRepository.
    """

    class Meta:
        fields = RepositorySerializer.Meta.fields
        model = AptRepository
