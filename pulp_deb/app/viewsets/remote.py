from gettext import gettext as _  # noqa

from pulpcore.plugin.viewsets import RemoteViewSet, RolesMixin

from pulp_deb.app import models, serializers


class AptRemoteViewSet(RemoteViewSet, RolesMixin):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An AptRemote represents an external APT repository content source.

    It contains the location of the upstream APT repository, as well as the user options that are
    applied when using the remote to synchronize the upstream repository to Pulp.
    """

    endpoint_name = "apt"
    queryset = models.AptRemote.objects.all()
    serializer_class = serializers.AptRemoteSerializer
    queryset_filtering_required_permission = "deb.view_aptremote"

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
                "condition": "has_model_or_domain_perms:deb.add_aptremote",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.view_aptremote",
            },
            {
                "action": ["update", "partial_update", "set_label", "unset_label"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.change_aptremote",
                    "has_model_or_domain_or_obj_perms:deb.view_aptremote",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_domain_or_obj_perms:deb.delete_aptremote",
                    "has_model_or_domain_or_obj_perms:deb.view_aptremote",
                ],
            },
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_domain_or_obj_perms:deb.manage_roles_aptremote",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {"roles": "deb.aptremote_owner"},
            }
        ],
        "queryset_scoping": {"function": "scope_queryset"},
    }

    LOCKED_ROLES = {
        "deb.aptremote_owner": [
            "deb.change_aptremote",
            "deb.delete_aptremote",
            "deb.manage_roles_aptremote",
            "deb.view_aptremote",
        ],
        "deb.aptremote_creator": [
            "deb.add_aptremote",
        ],
        "deb.aptremote_viewer": [
            "deb.view_aptremote",
        ],
    }
