from gettext import gettext as _
from django.conf import settings
from django.db import transaction
from pulpcore.plugin.models import SigningService
from pulpcore.plugin.serializers import (
    RelatedField,
    RepositorySerializer,
    RepositorySyncURLSerializer,
    ValidateFieldsMixin,
)
from pulpcore.plugin.util import get_url, get_domain

from pulp_deb.app.models import (
    AptRepositoryReleasePackageSigningFingerprintOverride,
    AptRepositoryReleaseServiceOverride,
    AptPackageSigningService,
    AptReleaseSigningService,
    AptRepository,
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


class PackageFingerprintOverrideField(serializers.DictField):
    child = serializers.CharField(max_length=40)

    def to_representation(self, overrides):
        return {x.release_distribution: x.package_signing_fingerprint for x in overrides.all()}


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

    package_signing_fingerprint_release_overrides = PackageFingerprintOverrideField(
        default=dict,
        required=False,
        help_text=_(
            "A dictionary of Release distributions and the "
            "Package Signing Fingerprints they should use."
            "Example: "
            '{"bionic": "7FC42CD5F3D8EEC3"}'
        ),
    )

    package_signing_service = RelatedField(
        help_text="A reference to an associated package signing service.",
        view_name="signing-services-detail",
        queryset=AptPackageSigningService.objects.all(),
        many=False,
        required=False,
        allow_null=True,
    )
    package_signing_fingerprint = serializers.CharField(
        help_text=_(
            "The pubkey V4 fingerprint (160 bits) to be passed to the package signing service."
            "The signing service will use that on signing operations related to this repository."
        ),
        max_length=40,
        required=False,
        allow_blank=True,
        default="",
    )

    class Meta:
        fields = RepositorySerializer.Meta.fields + (
            "autopublish",
            "publish_upstream_release_fields",
            "signing_service",
            "signing_service_release_overrides",
            "package_signing_fingerprint_release_overrides",
            "package_signing_service",
            "package_signing_fingerprint",
        )
        model = AptRepository

    @transaction.atomic
    def create(self, validated_data):
        """Create an AptRepository, special handling for signing_service_release_overrides."""
        service_overrides = validated_data.pop("signing_service_release_overrides", -1)
        fingerprint_overrides = validated_data.pop(
            "package_signing_fingerprint_release_overrides", -1
        )
        repo = super().create(validated_data)

        try:
            self._update_signing_service_overrides(repo, service_overrides)
            self._update_package_signing_fingerprint_overrides(repo, fingerprint_overrides)
        except DRFValidationError as exc:
            repo.delete()
            raise exc
        return repo

    def update(self, instance, validated_data):
        """Update an AptRepository, special handling for signing_service_release_overrides."""
        service_overrides = validated_data.pop("signing_service_release_overrides", -1)
        fingerprint_overrides = validated_data.pop(
            "package_signing_fingerprint_release_overrides", -1
        )
        with transaction.atomic():
            self._update_signing_service_overrides(instance, service_overrides)
            self._update_package_signing_fingerprint_overrides(instance, fingerprint_overrides)
            instance = super().update(instance, validated_data)
        return instance

    def _update_signing_service_overrides(self, repo, overrides):
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
                    current[distro].signing_service = signing_service
                    current[distro].save()
                else:  # create
                    AptRepositoryReleaseServiceOverride(
                        repository=repo,
                        signing_service=signing_service,
                        release_distribution=distro,
                    ).save()

    def _update_package_signing_fingerprint_overrides(self, repo, overrides):
        """Update package_signing_fingerprint_release_overrides."""
        if overrides == -1:
            # Sentinel value, no updates
            return

        current = {
            x.release_distribution: x
            for x in repo.package_signing_fingerprint_release_overrides.all()
        }
        # Intentionally only updates items the user specified.
        for distro, fingerprint in overrides.items():
            if not fingerprint and distro in current:  # the user wants to delete this override
                current[distro].delete()
            elif fingerprint:
                if distro in current:  # update
                    current[distro].package_signing_fingerprint = fingerprint
                    current[distro].save()
                else:  # create
                    AptRepositoryReleasePackageSigningFingerprintOverride(
                        repository=repo,
                        package_signing_fingerprint=fingerprint,
                        release_distribution=distro,
                    ).save()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "package_signing_fingerprint" in data and data["package_signing_fingerprint"] is None:
            data["package_signing_fingerprint"] = ""
        return data


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
