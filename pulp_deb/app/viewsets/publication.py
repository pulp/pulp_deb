from gettext import gettext as _  # noqa

from drf_spectacular.utils import extend_schema

from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import (
    DistributionViewSet,
    OperationPostponedResponse,
    PublicationViewSet,
)

from pulp_deb.app import models, serializers, tasks


class VerbatimPublicationViewSet(PublicationViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An VerbatimPublication is the Pulp-internal representation of a "mirrored" AptRepositoryVersion.

    In other words, the verbatim publisher will recreate the synced subset of some a APT
    repository using the exact same metadata files and signatures as used by the upstream original.
    Once a Pulp publication has been created, it can be served by creating a Pulp distribution (in
    a near atomic action).
    """

    endpoint_name = "verbatim"
    queryset = models.VerbatimPublication.objects.exclude(complete=False)
    serializer_class = serializers.VerbatimPublicationSerializer

    @extend_schema(
        description="Trigger an asynchronous task to publish content",
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

        result = dispatch(
            func=tasks.publish_verbatim,
            shared_resources=[repository_version.repository],
            kwargs={"repository_version_pk": repository_version.pk},
        )
        return OperationPostponedResponse(result, request)


class AptPublicationViewSet(PublicationViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptPublication is the ready to serve Pulp-internal representation of an AptRepositoryVersion.

    When creating an APT publication, users must use simple or structured mode (or both). If the
    publication should include '.deb' packages that were manually uploaded to the relevant
    AptRepository, users must use 'simple=true'. Conversely, 'structured=true' is only useful for
    publishing content obtained via synchronization. Once a Pulp publication has been created, it
    can be served by creating a Pulp distribution (in a near atomic action).
    """

    endpoint_name = "apt"
    queryset = models.AptPublication.objects.exclude(complete=False)
    serializer_class = serializers.AptPublicationSerializer

    @extend_schema(
        description="Trigger an asynchronous task to publish content",
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
        signing_service = serializer.validated_data.get("signing_service")
        publish_upstream_release_fields = serializer.validated_data.get(
            "publish_upstream_release_fields"
        )

        result = dispatch(
            func=tasks.publish,
            shared_resources=[repository_version.repository],
            kwargs={
                "repository_version_pk": repository_version.pk,
                "simple": simple,
                "structured": structured,
                "signing_service_pk": getattr(signing_service, "pk", None),
                "publish_upstream_release_fields": publish_upstream_release_fields,
            },
        )
        return OperationPostponedResponse(result, request)


class AptDistributionViewSet(DistributionViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptDistribution is just an AptPublication made available via the content app.

    Creating an AptDistribution is a comparatively quick action. This way Pulp users may take as
    much time as is needed to prepare a VerbatimPublication or AptPublication, and then control the
    exact moment when that publication is made available.
    """

    endpoint_name = "apt"
    queryset = models.AptDistribution.objects.all()
    serializer_class = serializers.AptDistributionSerializer
