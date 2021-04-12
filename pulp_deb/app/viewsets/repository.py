from gettext import gettext as _  # noqa

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
    RepositoryVersionViewSet,
    RepositoryViewSet,
)

from pulp_deb.app import models, serializers, tasks


class AptRepositoryViewSet(RepositoryViewSet, ModifyRepositoryActionMixin):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptRepository is the locally stored, Pulp-internal representation of a APT repository.

    It may be filled with content via synchronization or content upload to create an
    AptRepositoryVersion.
    """

    endpoint_name = "apt"
    queryset = models.AptRepository.objects.all()
    serializer_class = serializers.AptRepositorySerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @extend_schema(
        description="Trigger an asynchronous task to sync content",
        summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(
            data=request.data, context={"request": request, "repository_pk": pk}
        )

        # Validate synchronously to return 400 errors.
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote", repository.remote)
        mirror = serializer.validated_data.get("mirror", True)

        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={"remote_pk": remote.pk, "repository_pk": repository.pk, "mirror": mirror},
        )
        return OperationPostponedResponse(result, request)


class AptRepositoryVersionViewSet(RepositoryVersionViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptRepositoryVersion represents a single APT repository version as stored by Pulp.

    It may be used as the basis for the creation of Pulp distributions in order to actually serve
    the content contained within the repository version.
    """

    parent_viewset = AptRepositoryViewSet
