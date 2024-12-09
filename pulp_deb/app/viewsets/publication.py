from gettext import gettext as _  # noqa

from drf_spectacular.utils import extend_schema

from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import (
    DistributionViewSet,
    OperationPostponedResponse,
    PublicationViewSet,
    RolesMixin,
)

from pulp_deb.app import models, serializers, tasks


class VerbatimPublicationViewSet(PublicationViewSet, RolesMixin):
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
    queryset_filtering_required_permission = "deb.view_verbatimpublication"

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
                    "has_model_or_domain_perms:deb.add_verbatimpublication",
                    "has_repo_or_repo_ver_param_model_or_domain_or_obj_perms:"
                    "deb.view_aptrepository",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_verbatimpublication",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_verbatimpublication",
                    "has_model_or_domain_or_obj_perms:deb.view_verbatimpublication",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:"
                "deb.manage_roles_verbatimpublication",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.verbatimpublication_owner"},
            }
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }

    LOCKED_ROLES = {
        "deb.verbatimpublication_owner": [
            "deb.delete_verbatimpublication",
            "deb.manage_roles_verbatimpublication",
            "deb.view_verbatimpublication",
        ],
        "deb.verbatimpublication_creator": [
            "deb.add_verbatimpublication",
        ],
        "deb.verbatimpublication_viewer": [
            "deb.view_verbatimpublication",
        ],
    }

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


class AptPublicationViewSet(PublicationViewSet, RolesMixin):
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
    queryset_filtering_required_permission = "deb.view_aptpublication"

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
                    "has_model_or_domain_perms:deb.add_aptpublication",
                    "has_repo_or_repo_ver_param_model_or_domain_or_obj_perms:"
                    "deb.view_aptrepository",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_aptpublication",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_aptpublication",
                    "has_model_or_domain_or_obj_perms:deb.view_aptpublication",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.manage_roles_aptpublication",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.aptpublication_owner"},
            }
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }

    LOCKED_ROLES = {
        "deb.aptpublication_owner": [
            "deb.delete_aptpublication",
            "deb.manage_roles_aptpublication",
            "deb.view_aptpublication",
        ],
        "deb.aptpublication_creator": [
            "deb.add_aptpublication",
        ],
        "deb.aptpublication_viewer": [
            "deb.view_aptpublication",
        ],
    }

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


class AptDistributionViewSet(DistributionViewSet, RolesMixin):
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
    queryset_filtering_required_permission = "deb.view_aptdistribution"

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
                    "has_model_or_domain_perms:deb.add_aptdistribution",
                    "has_publication_param_model_or_domain_or_obj_perms:deb.view_aptpublication",
                    "has_repo_or_repo_ver_param_model_or_domain_or_obj_perms:"
                    "deb.view_aptrepository",
                ],
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_aptdistribution",
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.change_aptdistribution",
                    "has_model_or_domain_or_obj_perms:deb.view_aptdistribution",
                    "has_publication_param_model_or_domain_or_obj_perms:deb.view_aptpublication",
                    "has_repo_or_repo_ver_param_model_or_domain_or_obj_perms:"
                    "deb.view_aptrepository",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_aptdistribution",
                    "has_model_or_domain_or_obj_perms:deb.view_aptdistribution",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.manage_roles_aptdistribution",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.aptdistribution_owner"},
            }
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }

    LOCKED_ROLES = {
        "deb.aptdistribution_owner": [
            "deb.change_aptdistribution",
            "deb.delete_aptdistribution",
            "deb.manage_roles_aptdistribution",
            "deb.view_aptdistribution",
        ],
        "deb.aptdistribution_creator": [
            "deb.add_aptdistribution",
        ],
        "deb.aptdistribution_viewer": [
            "deb.view_aptdistribution",
        ],
    }
