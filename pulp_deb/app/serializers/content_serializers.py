from gettext import gettext as _
from logging import getLogger

import os

from debian import debfile

from rest_framework.serializers import CharField, Field, ValidationError
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    SingleArtifactContentUploadSerializer,
    DetailRelatedField,
)

from pulp_deb.app.models import (
    BasePackage,
    GenericContent,
    InstallerFileIndex,
    InstallerPackage,
    Package,
    PackageIndex,
    Release,
)


log = getLogger(__name__)


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


class GenericContentSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A serializer for GenericContent.
    """

    def deferred_validate(self, data):
        """Validate the GenericContent data."""

        data = super().deferred_validate(data)

        data["sha256"] = data["artifact"].sha256

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

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
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


class BasePackageSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A Serializer for abstract BasePackage.
    """

    package = CharField(read_only=True)
    source = CharField(read_only=True)
    version = CharField(read_only=True)
    architecture = CharField(read_only=True)
    section = CharField(read_only=True)
    priority = CharField(read_only=True)
    origin = CharField(read_only=True)
    tag = CharField(read_only=True)
    bugs = CharField(read_only=True)
    essential = YesNoField(read_only=True)
    build_essential = YesNoField(read_only=True)
    installed_size = CharField(read_only=True)
    maintainer = CharField(read_only=True)
    original_maintainer = CharField(read_only=True)
    description = CharField(read_only=True)
    description_md5 = CharField(read_only=True)
    homepage = CharField(read_only=True)
    built_using = CharField(read_only=True)
    auto_built_package = CharField(read_only=True)
    multi_arch = CharField(read_only=True)
    breaks = CharField(read_only=True)
    conflicts = CharField(read_only=True)
    depends = CharField(read_only=True)
    recommends = CharField(read_only=True)
    suggests = CharField(read_only=True)
    enhances = CharField(read_only=True)
    pre_depends = CharField(read_only=True)
    provides = CharField(read_only=True)
    replaces = CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        """Initializer for BasePackageSerializer."""
        super().__init__(*args, **kwargs)
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False

    def deferred_validate(self, data):
        """Validate that the artifact is a package and extract it's values."""

        data = super().deferred_validate(data)

        try:
            package_paragraph = debfile.DebFile(fileobj=data["artifact"].file).debcontrol()
        except Exception:  # TODO: Be more specific
            raise ValidationError(_("Not a valid Deb Package"))

        package_dict = self.Meta.model.from822(package_paragraph)
        data.update(package_dict)
        data["sha256"] = data["artifact"].sha256
        if "relative_path" not in data:
            data["relative_path"] = self.Meta.model(**package_dict).filename()
        elif not os.path.basename(data["relative_path"]) == "{}.{}".format(
            self.Meta.model(**package_dict).name, self.Meta.model.SUFFIX
        ):
            raise ValidationError(_("Invalid relative_path provided, filename does not match."))

        content = self.Meta.model.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a deb package with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        return data

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
            + (
                "package",
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
            )
        )
        model = BasePackage


class PackageSerializer(BasePackageSerializer):
    """
    A Serializer for Package.
    """

    def deferred_validate(self, data):
        """Validate for 'normal' Package (not installer)."""

        data = super().deferred_validate(data)

        if data.get("section") == "debian-installer":
            raise ValidationError(_("Not a valid Deb Package"))

        return data

    class Meta(BasePackageSerializer.Meta):
        model = Package


class InstallerPackageSerializer(BasePackageSerializer):
    """
    A Serializer for InstallerPackage.
    """

    def deferred_validate(self, data):
        """Validate for InstallerPackage."""

        data = super().deferred_validate(data)

        if data.get("section") != "debian-installer":
            raise ValidationError(_("Not a valid uDeb Package"))

        return data

    class Meta(BasePackageSerializer.Meta):
        model = InstallerPackage
