from gettext import gettext as _

from rest_framework.serializers import CharField, Field, ValidationError
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    SingleArtifactContentSerializer,
    DetailRelatedField,
    relative_path_validator,
)

from pulp_deb.app.models import (
    GenericContent,
    InstallerFileIndex,
    InstallerPackage,
    Package,
    PackageIndex,
    Release,
)


class YesNoField(Field):
    """
    A serializer field that accepts 'yes' or 'no' as boolean.
    """

    def to_representation(self, value):
        """
        Translate boolean to "yes/no".
        """
        if value is True:
            return "yes"
        elif value is False:
            return "no"

    def to_internal_value(self, data):
        """
        Translate "yes/no" to boolean.
        """
        data = data.strip().lower()
        if data == "yes":
            return True
        if data == "no":
            return False
        else:
            raise ValidationError('Value must be "yes" or "no".')


class GenericContentSerializer(SingleArtifactContentSerializer, ContentChecksumSerializer):
    """
    A serializer for GenericContent.
    """

    relative_path = CharField(
        help_text=_(
            "Relative location of the file within the repository. " "Example: `path/to/file.txt`"
        ),
        validators=[relative_path_validator],
        required=True,
    )

    def validate(self, data):
        """Validate the GenericContent data."""
        data = super().validate(data)

        data["sha256"] = data["_artifact"].sha256
        data["_relative_path"] = data["relative_path"]

        content = GenericContent.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )

        if content.exists():
            raise ValidationError(
                _(
                    "There is already a generic content with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        return data

    class Meta:
        fields = (
            tuple(set(SingleArtifactContentSerializer.Meta.fields) - {"_relative_path"})
            + ContentChecksumSerializer.Meta.fields
            + ("relative_path",)
        )
        model = GenericContent


class ReleaseSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for Release.
    """

    codename = CharField(help_text='Codename of the release, i.e. "buster".', required=True)

    suite = CharField(help_text='Suite of the release, i.e. "stable".', required=False)

    distribution = CharField(
        help_text='Distribution of the release, i.e. "stable/updates".', required=False
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "codename",
            "suite",
            "distribution",
            "relative_path",
        )
        model = Release


class PackageIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for PackageIndex.
    """

    component = CharField(
        help_text="Component of the component - architecture combination.", required=True
    )

    architecture = CharField(
        help_text="Architecture of the component - architecture combination.", required=True
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=Release.objects.all(),
        view_name="deb-release-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "architecture",
            "relative_path",
        )
        model = PackageIndex


class InstallerFileIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for InstallerFileIndex.
    """

    component = CharField(
        help_text="Component of the component - architecture combination.", required=True
    )

    architecture = CharField(
        help_text="Architecture of the component - architecture combination.", required=True
    )

    relative_path = CharField(
        help_text="Path of directory containing MD5SUMS and SHA256SUMS relative to url.",
        required=False,
    )

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=Release.objects.all(),
        view_name="deb-release-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "architecture",
            "relative_path",
        )
        model = InstallerFileIndex


class PackageSerializer(SingleArtifactContentSerializer):
    """
    A Serializer for Package.
    """

    essential = YesNoField(required=False)

    build_essential = YesNoField(required=False)

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            "package_name",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "bugs",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "description",
            "description_md5",
            "homepage",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "breaks",
            "conflicts",
            "depends",
            "recommends",
            "suggests",
            "enhances",
            "pre_depends",
            "provides",
            "replaces",
            "relative_path",
            "sha256",
        )
        model = Package


class InstallerPackageSerializer(SingleArtifactContentSerializer):
    """
    A Serializer for InstallerPackage.
    """

    essential = YesNoField(required=False)

    build_essential = YesNoField(required=False)

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            "package_name",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "bugs",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "description",
            "description_md5",
            "homepage",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "breaks",
            "conflicts",
            "depends",
            "recommends",
            "suggests",
            "enhances",
            "pre_depends",
            "provides",
            "replaces",
            "relative_path",
            "sha256",
        )
        model = InstallerPackage
