from drf_yasg.utils import swagger_auto_schema

from pulpcore.plugin import viewsets as core
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositoryPublishURLSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import enqueue_with_reservation
from rest_framework.decorators import detail_route

from . import models, serializers, tasks


class GenericContentFilter(core.ContentFilter):
    """
    FilterSet for GenericContent.
    """

    class Meta:
        model = models.GenericContent
        fields = [
            'relative_path',
        ]


class ReleaseFilter(core.ContentFilter):
    """
    FilterSet for Release.
    """

    class Meta:
        model = models.Release
        fields = [
            'codename',
            'suite',
            'relative_path',
        ]


class PackageFilter(core.ContentFilter):
    """
    FilterSet for Package.
    """

    class Meta:
        model = models.Package
        fields = [
            'relative_path',
        ]


class GenericContentViewSet(core.ContentViewSet):
    """
    A ViewSet for GenericContent.
    """

    endpoint_name = 'generic_contents'
    queryset = models.GenericContent.objects.all()
    serializer_class = serializers.GenericContentSerializer


class ReleaseViewSet(core.ContentViewSet):
    """
    A ViewSet for Release.
    """

    endpoint_name = 'releases'
    queryset = models.Release.objects.all()
    serializer_class = serializers.ReleaseSerializer


class PackageIndexViewSet(core.ContentViewSet):
    """
    A ViewSet for PackageIndex.
    """

    endpoint_name = 'package_index'
    queryset = models.PackageIndex.objects.all()
    serializer_class = serializers.PackageIndexSerializer


class PackageViewSet(core.ContentViewSet):
    """
    A ViewSet for Package.
    """

    endpoint_name = 'packages'
    queryset = models.Package.objects.all()
    serializer_class = serializers.PackageSerializer


class DebRemoteViewSet(core.RemoteViewSet):
    """
    A ViewSet for DebRemote.
    """

    endpoint_name = 'apt'
    queryset = models.DebRemote.objects.all()
    serializer_class = serializers.DebRemoteSerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to sync content",
        responses={202: AsyncOperationResponseSerializer}
    )
    @detail_route(methods=('post',), serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Synchronizes a repository.

        The ``repository`` field has to be provided.
        """
        remote = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={'request': request})

        # Validate synchronously to return 400 errors.
        serializer.is_valid(raise_exception=True)
        repository = serializer.validated_data.get('repository')
        mirror = serializer.validated_data.get('mirror', True)
        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={
                'remote_pk': remote.pk,
                'repository_pk': repository.pk,
                'mirror': mirror,
            }
        )
        return core.OperationPostponedResponse(result, request)


class DebVerbatimPublisherViewSet(core.PublisherViewSet):
    """
    A ViewSet for DebVerbatimPublisher.
    """

    endpoint_name = 'verbatim'
    queryset = models.DebVerbatimPublisher.objects.all()
    serializer_class = serializers.DebVerbatimPublisherSerializer

    # This decorator is necessary since a publish operation is asyncrounous and returns
    # the id and href of the publish task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer}
    )
    @detail_route(methods=('post',), serializer_class=RepositoryPublishURLSerializer)
    def publish(self, request, pk):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        publisher = self.get_object()
        serializer = RepositoryPublishURLSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get(
            'repository_version')

        result = enqueue_with_reservation(
            tasks.publish_verbatim,
            [repository_version.repository, publisher],
            kwargs={
                'publisher_pk': str(publisher.pk),
                'repository_version_pk': str(repository_version.pk)
            }
        )
        return core.OperationPostponedResponse(result, request)


class DebPublisherViewSet(core.PublisherViewSet):
    """
    A ViewSet for DebPublisher.
    """

    endpoint_name = 'apt'
    queryset = models.DebPublisher.objects.all()
    serializer_class = serializers.DebPublisherSerializer

    # This decorator is necessary since a publish operation is asyncrounous and returns
    # the id and href of the publish task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer}
    )
    @detail_route(methods=('post',), serializer_class=RepositoryPublishURLSerializer)
    def publish(self, request, pk):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        publisher = self.get_object()
        serializer = RepositoryPublishURLSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get('repository_version')

        result = enqueue_with_reservation(
            tasks.publish,
            [repository_version.repository, publisher],
            kwargs={
                'publisher_pk': str(publisher.pk),
                'repository_version_pk': str(repository_version.pk)
            }
        )
        return core.OperationPostponedResponse(result, request)
