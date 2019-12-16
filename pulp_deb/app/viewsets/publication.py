from gettext import gettext as _  # noqa

from drf_yasg.utils import swagger_auto_schema

from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.viewsets import (
    BaseDistributionViewSet,
    OperationPostponedResponse,
    PublicationViewSet,
)

from pulp_deb.app import models, serializers, tasks


class VerbatimPublicationViewSet(PublicationViewSet):
    """
    A ViewSet for VerbatimPublication.
    """

    endpoint_name = "verbatim"
    queryset = models.VerbatimPublication.objects.exclude(complete=False)
    serializer_class = serializers.VerbatimPublicationSerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get("repository_version")

        result = enqueue_with_reservation(
            tasks.publish_verbatim,
            [repository_version.repository],
            kwargs={"repository_version_pk": str(repository_version.pk)},
        )
        return OperationPostponedResponse(result, request)


class DebPublicationViewSet(PublicationViewSet):
    """
    A ViewSet for DebPublication.
    """

    endpoint_name = "apt"
    queryset = models.DebPublication.objects.exclude(complete=False)
    serializer_class = serializers.DebPublicationSerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get("repository_version")
        simple = serializer.validated_data.get("simple")
        structured = serializer.validated_data.get("structured")

        result = enqueue_with_reservation(
            tasks.publish,
            [repository_version.repository],
            kwargs={
                "repository_version_pk": str(repository_version.pk),
                "simple": simple,
                "structured": structured,
            },
        )
        return OperationPostponedResponse(result, request)


class DebDistributionViewSet(BaseDistributionViewSet):
    """
    ViewSet for DebDistributions.
    """

    endpoint_name = "apt"
    queryset = models.DebDistribution.objects.all()
    serializer_class = serializers.DebDistributionSerializer
