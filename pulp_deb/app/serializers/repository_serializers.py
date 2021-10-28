from gettext import gettext as _
from pulpcore.plugin.serializers import RepositorySerializer, validate_unknown_fields

from pulp_deb.app.models import AptRepository

from jsonschema import Draft7Validator
from rest_framework import serializers
from pulp_deb.app.schema import COPY_CONFIG_SCHEMA


class AptRepositorySerializer(RepositorySerializer):
    """
    A Serializer for AptRepository.
    """

    class Meta:
        fields = RepositorySerializer.Meta.fields
        model = AptRepository


class CopySerializer(serializers.Serializer):
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
        Set the DebRepository based on the RepositoryVersion if only the latter is provided.
        Set the RepositoryVersion based on the DebRepository if only the latter is provided.
        Convert the human-friendly names of the content types into what Pulp needs to query on.
        """
        super().validate(data)

        if hasattr(self, "initial_data"):
            validate_unknown_fields(self.initial_data, self.fields)

        if "config" in data:
            validator = Draft7Validator(COPY_CONFIG_SCHEMA)

            err = []
            for error in sorted(validator.iter_errors(data["config"]), key=str):
                err.append(error.message)
            if err:
                raise serializers.ValidationError(
                    _("Provided copy criteria is invalid:'{}'".format(err))
                )

        return data
