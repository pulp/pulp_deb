from gettext import gettext as _
from django.conf import settings
from django.db import transaction
from pulpcore.plugin.models import (
    SigningService,
    RepositoryVersion,
)
from pulpcore.plugin.serializers import (
    RelatedField,
    RepositorySerializer,
    RepositorySyncURLSerializer,
    ValidateFieldsMixin,
    RepositoryAddRemoveContentSerializer,
)
from pulpcore.plugin.util import get_url, get_domain
from pulpcore.app.util import extract_pk, raise_for_unknown_content_units

from pulp_deb.app.models import (
    AptRepositoryReleaseServiceOverride,
    AptReleaseSigningService,
    AptRepository,
    ReleaseComponent,
    ReleaseArchitecture,
    PackageReleaseComponent,
)

from jsonschema import Draft7Validator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from pulp_deb.app.schema import COPY_CONFIG_SCHEMA


class ServiceOverrideField(serializers.DictField):
    child = RelatedField(
        view_name="signing-services-detail",
        queryset=AptReleaseSigningService.objects.all(),
        many=False,
        required=False,
        allow_null=True,
    )

    def to_representation(self, overrides):
        return {
            # Cast to parent class so get_url can look up resource url.
            x.release_distribution: get_url(SigningService(x.signing_service.pk))
            for x in overrides.all()
        }


class AptRepositorySerializer(RepositorySerializer):
    """
    A Serializer for AptRepository.
    """

    autopublish = serializers.BooleanField(
        help_text=_(
            "Whether to automatically create publications for new repository versions, "
            "and update any distributions pointing to this repository. Will create a "
            "standard structured APT publication."
        ),
        default=False,
        required=False,
    )

    publish_upstream_release_fields = serializers.BooleanField(
        help_text=_(
            "Previously, pulp_deb only synced the Release file fields codename and suite, now "
            "version, origin, label, and description are also synced. Setting this setting to "
            "False will make Pulp revert to the old behaviour of using it's own internal values "
            "for the new fields during publish. This is primarily intended to avoid a sudden "
            "change in behaviour for existing Pulp repositories, since many Release file field "
            "changes need to be accepted by hosts consuming the published repository. The default "
            "for new repositories is True."
        ),
        required=False,
    )

    signing_service = RelatedField(
        help_text="A reference to an associated signing service. Used if "
        "AptPublication.signing_service is not set",
        view_name="signing-services-detail",
        queryset=AptReleaseSigningService.objects.all(),
        many=False,
        required=False,
        allow_null=True,
    )
    signing_service_release_overrides = ServiceOverrideField(
        default=dict,
        required=False,
        help_text=_(
            "A dictionary of Release distributions and the Signing Service URLs they should use."
            "Example: "
            '{"bionic": "/pulp/api/v3/signing-services/433a1f70-c589-4413-a803-c50b842ea9b5/"}'
        ),
    )

    class Meta:
        fields = RepositorySerializer.Meta.fields + (
            "autopublish",
            "publish_upstream_release_fields",
            "signing_service",
            "signing_service_release_overrides",
        )
        model = AptRepository

    @transaction.atomic
    def create(self, validated_data):
        """Create an AptRepository, special handling for signing_service_release_overrides."""
        overrides = validated_data.pop("signing_service_release_overrides", -1)
        repo = super().create(validated_data)

        try:
            self._update_overrides(repo, overrides)
        except DRFValidationError as exc:
            repo.delete()
            raise exc
        return repo

    def update(self, instance, validated_data):
        """Update an AptRepository, special handling for signing_service_release_overrides."""
        overrides = validated_data.pop("signing_service_release_overrides", -1)
        with transaction.atomic():
            self._update_overrides(instance, overrides)
            instance = super().update(instance, validated_data)
        return instance

    def _update_overrides(self, repo, overrides):
        """Update signing_service_release_overrides."""
        if overrides == -1:
            # Sentinel value, no updates
            return

        current = {x.release_distribution: x for x in repo.signing_service_release_overrides.all()}
        # Intentionally only updates items the user specified.
        for distro, service in overrides.items():
            if not service and distro in current:  # the user wants to delete this override
                current[distro].delete()
            elif service:
                signing_service = AptReleaseSigningService.objects.get(pk=service)
                if distro in current:  # update
                    current[distro] = signing_service
                    current[distro].save()
                else:  # create
                    AptRepositoryReleaseServiceOverride(
                        repository=repo,
                        signing_service=signing_service,
                        release_distribution=distro,
                    ).save()


class AptRepositorySyncURLSerializer(RepositorySyncURLSerializer):
    """
    A Serializer for AptRepository Sync.
    """

    optimize = serializers.BooleanField(
        help_text=_(
            "Using optimize sync, will skip the processing of metadata if the checksum has not "
            "changed since the last sync. This greately improves re-sync performance in such "
            "situations. If you feel the sync is missing something that has changed about the "
            "remote repository you are syncing, try using optimize=False for a full re-sync. "
            "Consider opening an issue on why we should not optimize in your use case."
        ),
        required=False,
        default=True,
    )


class CopySerializer(ValidateFieldsMixin, serializers.Serializer):
    """
    A serializer for Content Copy API.
    """

    config = serializers.JSONField(
        help_text=_("A JSON document describing sources, destinations, and content to be copied")
    )

    structured = serializers.BooleanField(
        help_text=_(
            "Also copy any distributions, components, and releases as needed for any packages "
            "being copied. This will allow for structured publications of the target repository."
            "Default is set to True"
        ),
        default=True,
    )

    dependency_solving = serializers.BooleanField(
        help_text=_(
            "Also copy dependencies of any packages being copied. NOT YET"
            'IMPLEMENTED! You must keep this at "False"!'
        ),
        default=False,
    )

    def validate(self, data):
        """
        Validate that the Serializer contains valid data.

        Make sure the config-JSON matches the config-schema.
        Check for cross-domain references (if domain-enabled).
        """

        def check_domain(domain, href, name):
            # We're doing just a string-check here rather than checking objects
            # because there can be A LOT of objects, and this is happening in the view-layer
            # where we have strictly-limited timescales to work with
            if href and domain not in href:
                raise serializers.ValidationError(
                    _("{} must be part of the {} domain.").format(name, domain)
                )

        def check_cross_domain_config(cfg):
            """Check that all config-elts are in 'our' domain."""
            # copy-cfg is a list of dictionaries.
            # source_repo_version and dest_repo are required fiels.
            # Insure curr-domain exists in src/dest/dest_base_version/content-list hrefs
            curr_domain_name = get_domain().name
            for entry in cfg:
                check_domain(curr_domain_name, entry["source_repo_version"], "dest_repo")
                check_domain(curr_domain_name, entry["dest_repo"], "dest_repo")
                check_domain(
                    curr_domain_name, entry.get("dest_base_version", None), "dest_base_version"
                )
                for content_href in entry.get("content", []):
                    check_domain(curr_domain_name, content_href, "content")

        super().validate(data)
        if "config" in data:
            # Make sure config is valid JSON
            validator = Draft7Validator(COPY_CONFIG_SCHEMA)

            err = []
            for error in sorted(validator.iter_errors(data["config"]), key=str):
                err.append(error.message)
            if err:
                raise serializers.ValidationError(
                    _("Provided copy criteria is invalid:'{}'".format(err))
                )

            if settings.DOMAIN_ENABLED:
                check_cross_domain_config(data["config"])

        return data


class AptRepositoryAddRemoveContentSerializer(RepositoryAddRemoveContentSerializer):
    """
    Extends RepositoryAddRemoveContentSerializer to support adding/removing
    - ReleaseComponents
    - ReleaseArchitectures
    - PackageReleaseComponents
    """

    add_release_components = serializers.ListField(
        help_text=_("A list of ReleaseComponents to associate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    remove_release_components = serializers.ListField(
        help_text=_("A list of ReleaseComponents to disassociate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    add_release_architectures = serializers.ListField(
        help_text=_("A list of ReleaseArchitectures to associate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    remove_release_architectures = serializers.ListField(
        help_text=_("A list of ReleaseArchitectures to disassociate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    add_package_release_components = serializers.ListField(
        help_text=_("A list of PackageReleaseComponents to associate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    remove_package_release_components = serializers.ListField(
        help_text=_("A list of PackageReleaseComponents to disassociate with a repository."),
        child=serializers.CharField(error_messages={"invalid": "Not a valid URI of a resource."}),
        required=False,
    )

    def validate_add_release_components(self, value):
        return self._validate_content_hrefs(value, ReleaseComponent)

    def validate_remove_release_components(self, value):
        return self._validate_content_hrefs(value, ReleaseComponent)

    def validate_add_release_architectures(self, value):
        return self._validate_content_hrefs(value, ReleaseArchitecture)

    def validate_remove_release_architectures(self, value):
        return self._validate_content_hrefs(value, ReleaseArchitecture)

    def validate_add_package_release_components(self, value):
        return self._validate_content_hrefs(value, PackageReleaseComponent)

    def validate_remove_package_release_components(self, value):
        return self._validate_content_hrefs(value, PackageReleaseComponent)

    def _validate_content_hrefs(self, value, model_class):
        """
        Validates that the requested Content exists.
        Similar to the validation done in "pulpcore/app/serializers/repository.py"
        for adding/removing content units
        """
        content_units = {}

        for url in value:
            content_units[extract_pk(url)] = url

        content_units_pks = set(content_units.keys())
        existing_content_units = model_class.objects.filter(pk__in=content_units_pks)
        existing_content_units.touch()

        raise_for_unknown_content_units(existing_content_units, content_units)

        return list(content_units.keys())

    class Meta:
        model = RepositoryVersion
        fields = RepositoryAddRemoveContentSerializer.Meta.fields + [
            "add_release_components",
            "remove_release_components",
            "add_release_architectures",
            "remove_release_architectures",
            "add_package_release_components",
            "remove_package_release_components",
        ]
