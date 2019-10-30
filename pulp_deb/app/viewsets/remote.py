from gettext import gettext as _  # noqa

from pulpcore.plugin.viewsets import RemoteViewSet

from pulp_deb.app import models, serializers


class DebRemoteViewSet(RemoteViewSet):
    """
    A ViewSet for DebRemote.
    """

    endpoint_name = "apt"
    queryset = models.DebRemote.objects.all()
    serializer_class = serializers.DebRemoteSerializer
