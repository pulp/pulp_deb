from gettext import gettext as _  # noqa

from pulpcore.plugin.viewsets import RemoteViewSet

from pulp_deb.app import models, serializers


class AptRemoteViewSet(RemoteViewSet):
    """
    A ViewSet for AptRemote.
    """

    endpoint_name = "apt"
    queryset = models.AptRemote.objects.all()
    serializer_class = serializers.AptRemoteSerializer
