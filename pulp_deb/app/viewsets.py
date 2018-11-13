from gettext import gettext as _

from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import detail_route
from rest_framework import serializers, status
from rest_framework.response import Response

from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositoryPublishURLSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.viewsets import (
    ContentViewSet,
    RemoteViewSet,
    OperationPostponedResponse,
    PublisherViewSet,
    BaseFilterSet)

from . import models, serializers, tasks


class GenericContentFilter(BaseFilterSet):
    """
    FilterSet for GenericContent.
    """

    class Meta:
        model = models.GenericContent
        fields = [
            'relative_path',
        ]


class ReleaseFilter(BaseFilterSet):
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


class PackageFilter(BaseFilterSet):
    """
    FilterSet for Package.
    """

    class Meta:
        model = models.Package
        fields = [
            'relative_path',
        ]


class GenericContentViewSet(ContentViewSet):
    """
    A ViewSet for GenericContent.
    """

    endpoint_name = 'deb/generic_contents'
    queryset = models.GenericContent.objects.all()
    serializer_class = serializers.GenericContentSerializer


class ReleaseViewSet(ContentViewSet):
    """
    A ViewSet for Release.
    """

    endpoint_name = 'deb/releases'
    queryset = models.Release.objects.all()
    serializer_class = serializers.ReleaseSerializer


class PackageIndexViewSet(ContentViewSet):
    """
    A ViewSet for PackageIndex.
    """

    endpoint_name = 'deb/package_index'
    queryset = models.PackageIndex.objects.all()
    serializer_class = serializers.PackageIndexSerializer


class PackageViewSet(ContentViewSet):
    """
    A ViewSet for Package.
    """

    endpoint_name = 'deb/packages'
    queryset = models.Package.objects.all()
    serializer_class = serializers.PackageSerializer


class DebRemoteViewSet(RemoteViewSet):
    """
    A ViewSet for DebRemote.
    """

    endpoint_name = 'deb'
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
        serializer = RepositorySyncURLSerializer(
            data=request.data, context={'request': request})

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
        return OperationPostponedResponse(result, request)


class DebVerbatimPublisherViewSet(PublisherViewSet):
    """
    A ViewSet for DebVerbatimPublisher.
    """

    endpoint_name = 'deb_verbatim'
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
        return OperationPostponedResponse(result, request)


class DebPublisherViewSet(PublisherViewSet):
    """
    A ViewSet for DebPublisher.
    """

    endpoint_name = 'deb'
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
        repository_version = serializer.validated_data.get(
            'repository_version')

        result = enqueue_with_reservation(
            tasks.publish,
            [repository_version.repository, publisher],
            kwargs={
                'publisher_pk': str(publisher.pk),
                'repository_version_pk': str(repository_version.pk)
            }
        )
        return OperationPostponedResponse(result, request)
