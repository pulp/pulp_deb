from gettext import gettext as _

import os

from debian import deb822, debfile

from rest_framework.serializers import CharField, DictField, Field, ValidationError
from pulpcore.plugin.models import Artifact, RemoteArtifact
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    NoArtifactContentSerializer,
    SingleArtifactContentSerializer,
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
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    ReleaseFile,
)

from pulp_deb.app.models.content import BOOL_CHOICES

import logging

log = logging.getLogger(__name__)


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
            content.first().touch()  # Orphan cleanup protection so the user has a chance to use it!
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


class ReleaseFileSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for ReleaseFile.
    """

    codename = CharField(help_text='Codename of the release, i.e. "buster".', required=False)

    suite = CharField(help_text='Suite of the release, i.e. "stable".', required=False)

    distribution = CharField(
        help_text='Distribution of the release, i.e. "stable/updates".', required=True
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "codename",
            "suite",
            "distribution",
            "relative_path",
        )
        model = ReleaseFile


class PackageIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for PackageIndex.
    """

    component = CharField(
        help_text="Component of the component - architecture combination.", required=False
    )

    architecture = CharField(
        help_text="Architecture of the component - architecture combination.", required=False
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=ReleaseFile.objects.all(),
        view_name="deb-release-file-detail",
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
        queryset=ReleaseFile.objects.all(),
        view_name="deb-release-file-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "architecture",
            "relative_path",
        )
        model = InstallerFileIndex


class BasePackage822Serializer(SingleArtifactContentSerializer):
    """
    A Serializer for abstract BasePackage used for conversion from 822 format.
    """

    TRANSLATION_DICT = {
        "package": "Package",
        "source": "Source",
        "version": "Version",
        "architecture": "Architecture",
        "section": "Section",
        "priority": "Priority",
        "origin": "Origin",
        "tag": "Tag",
        "bugs": "Bugs",
        "essential": "Essential",
        "build_essential": "Build-Essential",
        "installed_size": "Installed-Size",
        "maintainer": "Maintainer",
        "original_maintainer": "Original-Maintainer",
        "description": "Description",
        "description_md5": "Description-md5",
        "homepage": "Homepage",
        "built_using": "Built-Using",
        "auto_built_package": "Auto_Built_Package",
        "multi_arch": "Multi-Arch",
        "breaks": "Breaks",
        "conflicts": "Conflicts",
        "depends": "Depends",
        "recommends": "Recommends",
        "suggests": "Suggests",
        "enhances": "Enhances",
        "pre_depends": "Pre-Depends",
        "provides": "Provides",
        "replaces": "Replaces",
    }
    TRANSLATION_DICT_INV = {v: k for k, v in TRANSLATION_DICT.items()}

    package = CharField()
    source = CharField(required=False)
    version = CharField()
    architecture = CharField()
    section = CharField(required=False)
    priority = CharField(required=False)
    origin = CharField(required=False)
    tag = CharField(required=False)
    bugs = CharField(required=False)
    essential = YesNoField(required=False)
    build_essential = YesNoField(required=False)
    installed_size = CharField(required=False)
    maintainer = CharField()
    original_maintainer = CharField(required=False)
    description = CharField()
    description_md5 = CharField(required=False)
    homepage = CharField(required=False)
    built_using = CharField(required=False)
    auto_built_package = CharField(required=False)
    multi_arch = CharField(required=False)
    breaks = CharField(required=False)
    conflicts = CharField(required=False)
    depends = CharField(required=False)
    recommends = CharField(required=False)
    suggests = CharField(required=False)
    enhances = CharField(required=False)
    pre_depends = CharField(required=False)
    provides = CharField(required=False)
    replaces = CharField(required=False)
    custom_fields = DictField(child=CharField(), allow_empty=True, required=False)

    def __init__(self, *args, **kwargs):
        """Initializer for BasePackage822Serializer."""
        super().__init__(*args, **kwargs)
        self.fields.pop("artifact")
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False

    @classmethod
    def from822(cls, data, **kwargs):
        """
        Translate deb822.Package to a dictionary for class instatiation.
        """
        skip = ["Filename", "MD5sum", "Size", "SHA1", "SHA256", "SHA512"]
        package_fields = {}
        custom_fields = {}
        for k, v in data.items():
            if k in cls.TRANSLATION_DICT_INV:
                key = cls.TRANSLATION_DICT_INV[k]
                package_fields[key] = v
            elif k not in skip:
                # also save the fields not in TRANSLATION_DICT
                custom_fields[k] = v

        unique_package_name = "{}_{}_{}".format(
            package_fields["package"],
            package_fields["version"],
            package_fields["architecture"],
        )

        # Drop keys with empty values
        empty_fields = [k for k, v in package_fields.items() if not v]
        for key in empty_fields:
            message = _('Dropping empty "{}" field from "{}" package!').format(
                key, unique_package_name
            )
            log.warning(message)
            del package_fields[key]

        # Delete package fields with values of incorrect type
        if "installed_size" in package_fields:
            try:
                int(package_fields["installed_size"])
            except (TypeError, ValueError):
                log.warn(
                    _(
                        "Dropping 'Installed-Size' field from '{}', "
                        "since the value '{}' is of incorrect type."
                    ).format(unique_package_name, package_fields["installed_size"])
                )
                del package_fields["installed_size"]
        message = _(
            "Dropping '{}' field from package '{}', "
            "since the value '{}' is not in the allowed values list '{}'"
        )
        bool_values = [value[1] for value in BOOL_CHOICES]
        if "essential" in package_fields and package_fields["essential"] not in bool_values:
            log.warn(
                message.format(
                    "Essential", unique_package_name, package_fields["essential"], bool_values
                )
            )
            del package_fields["essential"]
        if (
            "build_essential" in package_fields
            and package_fields["build_essential"] not in bool_values
        ):
            log.warn(
                message.format(
                    "Build-Essential",
                    unique_package_name,
                    package_fields["build_essential"],
                    bool_values,
                )
            )
            del package_fields["build_essential"]
        if "multi_arch" in package_fields:
            allowed_values = [value[1] for value in BasePackage.MULTIARCH_CHOICES]
            if package_fields["multi_arch"] not in allowed_values:
                log.warn(
                    message.format(
                        "Multi-Arch",
                        unique_package_name,
                        package_fields["multi_arch"],
                        allowed_values,
                    )
                )
                del package_fields["multi_arch"]

        package_fields["custom_fields"] = custom_fields
        return cls(data=package_fields, **kwargs)

    def to822(self, component=""):
        """Create deb822.Package object from model."""
        ret = deb822.Packages()

        for k, v in self.TRANSLATION_DICT.items():
            value = self.data.get(k)
            if value is not None:
                ret[v] = value

        custom_fields = self.data.get("custom_fields")
        if custom_fields:
            ret.update(custom_fields)

        try:
            artifact = self.instance._artifacts.get()
            artifact.touch()  # Orphan cleanup protection until we are done!
            if artifact.md5:
                ret["MD5sum"] = artifact.md5
            if artifact.sha1:
                ret["SHA1"] = artifact.sha1
            ret["SHA256"] = artifact.sha256
            ret["Size"] = str(artifact.size)
        except Artifact.DoesNotExist:
            artifact = RemoteArtifact.objects.filter(sha256=self.instance.sha256).first()
            if artifact.md5:
                ret["MD5sum"] = artifact.md5
            if artifact.sha1:
                ret["SHA1"] = artifact.sha1
            ret["SHA256"] = artifact.sha256
            ret["Size"] = str(artifact.size)

        ret["Filename"] = self.instance.filename(component)

        return ret

    class Meta(SingleArtifactContentSerializer.Meta):
        fields = SingleArtifactContentSerializer.Meta.fields + (
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
            "custom_fields",
        )
        model = BasePackage


class Package822Serializer(BasePackage822Serializer):
    """
    A Serializer for Package used for conversion from 822 format.
    """

    class Meta(BasePackage822Serializer.Meta):
        model = Package


class InstallerPackage822Serializer(BasePackage822Serializer):
    """
    A Serializer for InstallerPackage used for conversion from 822 format.
    """

    class Meta(BasePackage822Serializer.Meta):
        model = InstallerPackage


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
    custom_fields = DictField(child=CharField(), allow_empty=True, required=False)

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
        except debfile.DebError as e:
            if "[Errno 2] No such file or directory: 'unzstd'" in "{}".format(e):
                message = (
                    "The package file provided uses zstd compression, but the unzstd binary is not "
                    "available! Make sure the zstd package (depending on your package manager) is "
                    "installed."
                )
            else:
                message = (
                    "python-debian was unable to read the provided package file! The error is '{}'."
                )
            raise ValidationError(_(message).format(e))

        from822_serializer = self.Meta.from822_serializer.from822(data=package_paragraph)
        from822_serializer.is_valid(raise_exception=True)
        package_data = from822_serializer.validated_data
        data.update(package_data)
        data["sha256"] = data["artifact"].sha256

        if "relative_path" not in data:
            data["relative_path"] = self.Meta.model(**package_data).filename()
        elif not os.path.basename(data["relative_path"]) == "{}.{}".format(
            self.Meta.model(**package_data).name, self.Meta.model.SUFFIX
        ):
            data["artifact"].touch()  # Orphan cleanup protection so the user can try again!
            raise ValidationError(_("Invalid relative_path provided, filename does not match."))

        content = self.Meta.model.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            content.first().touch()  # Orphan cleanup protection so the user has a chance to use it!
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
        from822_serializer = Package822Serializer


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
        from822_serializer = InstallerPackage822Serializer


class ReleaseSerializer(NoArtifactContentSerializer):
    """
    A Serializer for Release.
    """

    codename = CharField()
    suite = CharField()
    distribution = CharField()

    class Meta(NoArtifactContentSerializer.Meta):
        model = Release
        fields = NoArtifactContentSerializer.Meta.fields + ("codename", "suite", "distribution")


class ReleaseArchitectureSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseArchitecture.
    """

    architecture = CharField(help_text="Name of the architecture.")
    release = DetailRelatedField(
        help_text="Release this architecture is contained in.",
        many=False,
        queryset=Release.objects.all(),
        view_name="content-deb/releases-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseArchitecture
        fields = NoArtifactContentSerializer.Meta.fields + ("architecture", "release")


class ReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseComponent.
    """

    component = CharField(help_text="Name of the component.")
    release = DetailRelatedField(
        help_text="Release this component is contained in.",
        many=False,
        queryset=Release.objects.all(),
        view_name="content-deb/releases-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("component", "release")


class PackageReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for PackageReleaseComponent.
    """

    package = DetailRelatedField(
        help_text="Package that is contained in release_comonent.",
        many=False,
        queryset=Package.objects.all(),
        view_name="content-deb/packages-detail",
    )
    release_component = DetailRelatedField(
        help_text="ReleaseComponent this package is contained in.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="content-deb/release_components-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = PackageReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("package", "release_component")
