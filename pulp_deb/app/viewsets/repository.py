from gettext import gettext as _  # noqa

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.serializers import ValidationError as DRFValidationError

from pulp_deb.app.models.content.content import Package
from pulp_deb.app.models.content.structure_content import PackageReleaseComponent
from pulp_deb.app.serializers import (
    AptRepositorySyncURLSerializer,
    AptRepositoryAddRemoveContentSerializer,
)
from pulpcore.plugin.util import extract_pk, get_url
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
)
from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
    RepositoryVersionViewSet,
    RepositoryViewSet,
    NamedModelViewSet,
    RolesMixin,
)

from pulp_deb.app import models, serializers, tasks


class AptModifyRepositoryActionMixin(ModifyRepositoryActionMixin):
    @extend_schema(
        description="Trigger an asynchronous task to create a new repository version.",
        summary="Modify Repository Content",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=AptRepositoryAddRemoveContentSerializer)
    def modify(self, request, pk):
        data = request.data
        remove_content_units = data.get("remove_content_units", [])
        package_hrefs = [href for href in remove_content_units if "/packages/" in href]

        if package_hrefs:
            prc_hrefs = self._get_matching_prc_hrefs(package_hrefs)
            remove_content_units.extend(prc_hrefs)

        # Merge also add/remove RC, RA and PRCs into add/remove content units
        data["add_content_units"] = (
            data.get("add_content_units", [])
            + data.get("add_release_components", [])
            + data.get("add_release_architectures", [])
            + data.get("add_package_release_components", [])
        )

        data["remove_content_units"] = (
            remove_content_units
            + data.get("remove_release_components", [])
            + data.get("remove_release_architectures", [])
            + data.get("remove_package_release_components", [])
        )

        return super().modify(request, pk)

    def _get_matching_prc_hrefs(self, package_hrefs):
        package_ids = [extract_pk(href) for href in package_hrefs]
        matching_packages = Package.objects.filter(pulp_id__in=package_ids)
        matching_prcs = PackageReleaseComponent.objects.filter(package__in=matching_packages)
        prc_hrefs = [get_url(component) for component in matching_prcs]
        return prc_hrefs


class AptRepositoryViewSet(AptModifyRepositoryActionMixin, RepositoryViewSet, RolesMixin):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptRepository is the locally stored, Pulp-internal representation of a APT repository.

    It may be filled with content via synchronization or content upload to create an
    AptRepositoryVersion.
    """

    endpoint_name = "apt"
    queryset = models.AptRepository.objects.all()
    serializer_class = serializers.AptRepositorySerializer
    queryset_filtering_required_permission = "deb.view_aptrepository"

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "my_permissions"],
                "principal": ["authenticated"],
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_remote_param_model_or_domain_or_obj_perms:deb.view_aptremote",
                    "has_model_or_domain_perms:deb.add_aptrepository",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_aptrepository",
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.change_aptrepository",
                    "has_model_or_domain_or_obj_perms:deb.view_aptrepository",
                    "has_remote_param_model_or_domain_or_obj_perms:deb.view_aptremote",
                ],
            },
            {
                "action": ["modify"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.modify_content_aptrepository",
                    "has_model_or_domain_or_obj_perms:deb.view_aptrepository",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_aptrepository",
                    "has_model_or_domain_or_obj_perms:deb.view_aptrepository",
                ],
            },
            {
                "action": ["sync"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.sync_aptrepository",
                    "has_model_or_domain_or_obj_perms:deb.view_aptrepository",
                    "has_remote_param_model_or_domain_or_obj_perms:deb.view_aptremote",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.manage_roles_aptrepository",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.aptrepository_owner"},
            }
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }

    LOCKED_ROLES = {
        "deb.aptrepository_owner": [
            "deb.change_aptrepository",
            "deb.delete_aptrepository",
            "deb.delete_aptrepository_version",
            "deb.manage_roles_aptrepository",
            "deb.modify_content_aptrepository",
            "deb.repair_aptrepository",
            "deb.sync_aptrepository",
            "deb.view_aptrepository",
        ],
        "deb.aptrepository_creator": [
            "deb.add_aptrepository",
        ],
        "deb.aptrepository_viewer": [
            "deb.view_aptrepository",
        ],
        # A locked role to allow all APT permissions
        "deb.admin": [
            "deb.add_aptdistribution",
            "deb.add_aptpublication",
            "deb.add_aptremote",
            "deb.add_aptrepository",
            "deb.add_verbatimpublication",
            "deb.change_aptdistribution",
            "deb.change_aptremote",
            "deb.change_aptrepository",
            "deb.delete_aptdistribution",
            "deb.delete_aptpublication",
            "deb.delete_aptremote",
            "deb.delete_aptrepository",
            "deb.delete_aptrepository_version",
            "deb.delete_verbatimpublication",
            "deb.manage_roles_aptdistribution",
            "deb.manage_roles_aptpublication",
            "deb.manage_roles_aptremote",
            "deb.manage_roles_aptrepository",
            "deb.manage_roles_verbatimpublication",
            "deb.modify_content_aptrepository",
            "deb.repair_aptrepository",
            "deb.sync_aptrepository",
            "deb.view_aptdistribution",
            "deb.view_aptpublication",
            "deb.view_aptremote",
            "deb.view_aptrepository",
            "deb.view_verbatimpublication",
        ],
        # A locked role to allow APT view permissions
        "deb.viewer": [
            "deb.view_aptdistribution",
            "deb.view_aptpublication",
            "deb.view_aptremote",
            "deb.view_aptrepository",
            "deb.view_verbatimpublication",
        ],
    }

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

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list", "retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_repository_model_or_domain_or_obj_perms:deb.view_aptrepository",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_repository_model_or_domain_or_obj_perms:deb.delete_aptrepository_version",
                    "has_repository_model_or_domain_or_obj_perms:deb.view_aptrepository",
                ],
            },
            {
                "action": ["repair"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_repository_model_or_domain_or_obj_perms:deb.repair_aptrepository",
                    "has_repository_model_or_domain_or_obj_perms:deb.view_aptrepository",
                ],
            },
        ],
    }


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
                    message = _(
                        "Version {version} does not exist for repository " "'{repo}'."
                    ).format(version=entry["dest_base_version"], repo=dest_repo.name)
                    raise DRFValidationError(detail=message)

            if entry.get("content") is not None:
                r["content"] = []
                for c in entry["content"]:
                    r["content"].append(extract_pk(c))
            result.append(r)

        return result, shared_repos, exclusive_repos
