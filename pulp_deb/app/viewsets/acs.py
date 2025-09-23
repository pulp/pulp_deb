import os

from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404

from pulpcore.plugin.models import AlternateContentSourcePath, TaskGroup
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.serializers import TaskGroupOperationResponseSerializer
from pulpcore.plugin.viewsets import (
    AlternateContentSourceViewSet,
    RolesMixin,
    TaskGroupOperationResponse,
)

from pulp_deb.app import tasks
from pulp_deb.app.models import (
    AptAlternateContentSource,
    AptRepository,
)
from pulp_deb.app.serializers import (
    AptAlternateContentSourceSerializer,
    AptRepositorySyncURLSerializer,
)


class AptAlternateContentsourceViewSet(AlternateContentSourceViewSet, RolesMixin):
    """
    ViewSet for ACS.
    """

    endpoint_name = "deb"
    queryset = AptAlternateContentSource.objects.all()
    serializer_class = AptAlternateContentSourceSerializer
    queryset_filtering_required_permission = "deb.view_aptalternatecontentsource"

    DEFAULT_ACCESS_POLICY = {
        "statements": [
            {
                "action": ["list"],
                "principal": ["authenticated"],
                "effect": "allow",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_aptalternatecontentsource",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_remote_param_model_or_domain_or_obj_perms:deb.view_aptremote",
                    "has_model_or_domain_perms:deb.add_aptalternatecontentsource",
                ],
            },
            {
                "action": ["refresh"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.view_aptalternatecontentsource",
                    "has_model_or_domain_perms:deb.refresh_aptalternatecontentsource",
                ],
            },
            {
                "action": ["update", "partial_update"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.change_aptalternatecontentsource",
                    "has_model_or_domain_or_obj_perms:deb.view_aptalternatecontentsource",
                    "has_remote_param_model_or_domain_or_obj_perms:deb.view_aptremote",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_aptalternatecontentsource",
                    "has_model_or_domain_or_obj_perms:deb.view_aptalternatecontentsource",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": (
                    "has_model_or_domain_or_obj_perms:" "deb.manage_roles_aptalternatecontentsource"
                ),
            },
        ],
        "queryset_scoping": {"function": "scope_queryset"},
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.debalternatecontentsource_owner"},
            }
        ],
    }

    LOCKED_ROLES = {
        "deb.debalternatecontentsource_owner": [
            "deb.change_aptalternatecontentsource",
            "deb.delete_aptalternatecontentsource",
            "deb.manage_roles_aptalternatecontentsource",
            "deb.refresh_aptalternatecontentsource",
            "deb.view_aptalternatecontentsource",
        ],
        "deb.debalternatecontentsource_creator": [
            "deb.add_aptalternatecontentsource",
        ],
        "deb.debalternatecontentsource_viewer": [
            "deb.view_aptalternatecontentsource",
        ],
    }

    @extend_schema(
        description="Trigger an asynchronous task to create Alternate Content Source content.",
        responses={202: TaskGroupOperationResponseSerializer},
        request=None,
    )
    @action(methods=["post"], detail=True)
    def refresh(self, request, pk):
        """
        Refresh ACS metadata.
        """
        acs = get_object_or_404(AptAlternateContentSource, pk=pk)
        acs_paths = AlternateContentSourcePath.objects.filter(alternate_content_source=pk)
        task_group = TaskGroup.objects.create(
            description=f"Refreshing {acs_paths.count()} alternate content source path(s)."
        )

        # Get required defaults for sync operation
        optimize = AptRepositorySyncURLSerializer().data.get("optimize", True)

        for acs_path in acs_paths:
            # Create or get repository for the path
            repo_data = {
                "name": f"{acs.name}--{acs_path.pk}--repository",
                "retain_repo_version": 1,
                "user_hidden": True,
            }
            repo, created = AptRepository.objects.get_or_create(**repo_data)
            if created:
                acs_path.repository = repo
                acs_path.save()
            acs_url = (
                os.path.join(acs.remote.url, acs_path.path) if acs_path.path else acs.remote.url
            )

            # Dispatching ACS path to own task and assign it to common TaskGroup
            dispatch(
                tasks.synchronize,
                shared_resources=[acs.remote, acs],
                task_group=task_group,
                kwargs={
                    "remote_pk": str(acs.remote.pk),
                    "repository_pk": str(acs_path.repositoy.pk),
                    "mirror": True,
                    "optimize": optimize,
                    "url": acs_url,
                },
            )

        acs.last_refreshed = now()
        acs.save()

        return TaskGroupOperationResponse(task_group, request)
