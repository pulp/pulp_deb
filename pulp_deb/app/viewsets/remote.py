from gettext import gettext as _  # noqa

from pulpcore.plugin.viewsets import RemoteViewSet

from pulp_deb.app import models, serializers


class AptRemoteViewSet(RemoteViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptRemote represents an external APT repository content source.

    It contains the location of the upstream APT repository, as well as the user options that are
    applied when using the remote to synchronize the upstream repository to Pulp.
    """

    endpoint_name = "apt"
    queryset = models.AptRemote.objects.all()
    serializer_class = serializers.AptRemoteSerializer
