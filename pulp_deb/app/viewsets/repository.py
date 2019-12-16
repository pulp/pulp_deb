from gettext import gettext as _  # noqa

from drf_yasg.utils import swagger_auto_schema
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


class DebRepositoryViewSet(RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for DebRepository.
    """

    endpoint_name = "apt"
    queryset = models.DebRepository.objects.all()
    serializer_class = serializers.DebRepositorySerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to sync content",
        operation_summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={"request": request})

        # Validate synchronously to return 400 errors.
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote")
        mirror = serializer.validated_data.get("mirror", True)

        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={"remote_pk": remote.pk, "repository_pk": repository.pk, "mirror": mirror},
        )
        return OperationPostponedResponse(result, request)


class DebRepositoryVersionViewSet(RepositoryVersionViewSet):
    """
    DebRepositoryVersion represents a single deb repository version.
    """

    parent_viewset = DebRepositoryViewSet
