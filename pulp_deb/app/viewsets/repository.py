from gettext import gettext

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.serializers import ValidationError as DRFValidationError

from pulp_deb.app.serializers import AptRepositorySyncURLSerializer

from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
    RepositoryVersionViewSet,
    RepositoryViewSet,
    NamedModelViewSet,
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
    @action(detail=True, methods=["post"], serializer_class=AptRepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = AptRepositorySyncURLSerializer(
            data=request.data, context={"request": request, "repository_pk": pk}
        )

        # Validate synchronously to return 400 errors.
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote", repository.remote)
        mirror = serializer.validated_data.get("mirror")
        optimize = serializer.validated_data.get("optimize")

        result = dispatch(
            func=tasks.synchronize,
            exclusive_resources=[repository],
            shared_resources=[remote],
            kwargs={
                "remote_pk": remote.pk,
                "repository_pk": repository.pk,
                "mirror": mirror,
                "optimize": optimize,
            },
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


class CopyViewSet(viewsets.ViewSet):
    """
    ViewSet for the content copy API endpoint.
    """

    serializer_class = serializers.CopySerializer

    @extend_schema(
        description="Trigger an asynchronous task to copy APT content"
        "from one repository into another, creating a new"
        "repository version.",
        summary="Copy content",
        operation_id="copy_content",
        request=serializers.CopySerializer,
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """Copy content."""
        serializer = serializers.CopySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        config = serializer.validated_data["config"]
        structured = serializer.validated_data["structured"]
        dependency_solving = serializer.validated_data["dependency_solving"]

        config, shared_repos, exclusive_repos = self._process_config(config)

        async_result = dispatch(
            tasks.copy_content,
            shared_resources=shared_repos,
            exclusive_resources=exclusive_repos,
            args=[config, structured, dependency_solving],
            kwargs={},
        )
        return OperationPostponedResponse(async_result, request)

    def _process_config(self, config):
        """
        Change the hrefs into pks within config.
        This method also implicitly validates that the hrefs map to objects and it returns a list of
        repos so that the task can lock on them.
        """
        result = []
        # exclusive use of the destination repos is needed since new repository versions are being
        # created, but source repos can be accessed in a read-only fashion in parallel, so long
        # as there are no simultaneous modifications.
        shared_repos = []
        exclusive_repos = []

        for entry in config:
            r = dict()
            source_version = NamedModelViewSet().get_resource(
                entry["source_repo_version"], RepositoryVersion
            )
            dest_repo = NamedModelViewSet().get_resource(entry["dest_repo"], models.AptRepository)
            r["source_repo_version"] = source_version.pk
            r["dest_repo"] = dest_repo.pk
            shared_repos.append(source_version.repository)
            exclusive_repos.append(dest_repo)

            if "dest_base_version" in entry:
                try:
                    r["dest_base_version"] = dest_repo.versions.get(
                        number=entry["dest_base_version"]
                    ).pk
                except RepositoryVersion.DoesNotExist:
                    message = gettext(
                        "Version {version} does not exist for repository " "'{repo}'."
                    ).format(version=entry["dest_base_version"], repo=dest_repo.name)
                    raise DRFValidationError(detail=message)

            if entry.get("content") is not None:
                r["content"] = []
                for c in entry["content"]:
                    r["content"].append(NamedModelViewSet().extract_pk(c))
            result.append(r)

        return result, shared_repos, exclusive_repos
