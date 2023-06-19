from contextlib import suppress
from gettext import gettext as _

import os

from debian import deb822, debfile
from django.db import IntegrityError

from rest_framework.serializers import CharField, DictField, Field, ValidationError, Serializer
from pulpcore.plugin.models import Artifact, RemoteArtifact
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    NoArtifactContentSerializer,
    SingleArtifactContentSerializer,
    SingleArtifactContentUploadSerializer,
    DetailRelatedField,
)
from pulp_deb.app.constants import (
    PACKAGE_UPLOAD_DEFAULT_COMPONENT,
    PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION,
)

from pulp_deb.app.constants import NULL_VALUE
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

from pulp_deb.app.models import BOOL_CHOICES

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


class NullableCharField(CharField):
    """
    A serializer that accepts null values but saves them as the NULL_VALUE str.
    """

    def to_representation(self, value):
        """
        Translate str to str or None.
        """
        if value == NULL_VALUE:
            return None
        else:
            return value

    def to_internal_value(self, data):
        """
        Translate None to NULL_VALUE str.
        """
        if data is None:
            return NULL_VALUE
        else:
            return data

    def validate_empty_values(self, data):
        """
        Translate None to NULL_VALUE str.

        This is needed when user input is not set, it defaults to None and the to_internal_value
        method never gets called.
        """
        (is_empty_value, data) = super().validate_empty_values(data)
        if is_empty_value and data is None:
            return is_empty_value, NULL_VALUE
        return is_empty_value, data


class GenericContentSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A serializer for GenericContent.
    """

    def deferred_validate(self, data):
        """Validate the GenericContent data."""
        data = super().deferred_validate(data)

        data["sha256"] = data["artifact"].sha256

        return data

    def retrieve(self, validated_data):
        content = GenericContent.objects.filter(
            sha256=validated_data["sha256"], relative_path=validated_data["relative_path"]
        )

        return content.first()

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

    codename = CharField(help_text='Codename of the release, e.g. "buster".', required=False)

    suite = CharField(help_text='Suite of the release, e.g. "stable".', required=False)

    distribution = CharField(
        help_text='Distribution of the release, e.g. "stable/updates".', required=True
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

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
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

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "component",
            "architecture",
            "relative_path",
        )
        model = InstallerFileIndex


class SinglePackageUploadSerializer(SingleArtifactContentUploadSerializer):
    """
    A serializer for content_types with a single Package.
    """

    distribution = CharField(help_text="Name of the distribution.", required=False)
    component = CharField(help_text="Name of the component.", required=False)

    def create(self, validated_data):
        distribution = (
            validated_data.pop("distribution", None)
            if "distribution" in validated_data
            else PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION
        )
        component = (
            validated_data.pop("component", None)
            if "component" in validated_data
            else PACKAGE_UPLOAD_DEFAULT_COMPONENT
        )

        if validated_data.get("repository"):
            repository = validated_data.pop("repository", None)
            repository.cast()
            result = super().create(validated_data)
            content_to_add = self.Meta.model.objects.filter(pk=result.pk)
            with suppress(IntegrityError):
                release_component = ReleaseComponent(distribution=distribution, component=component)
                release_component.save()
                release_component_to_add = ReleaseComponent.objects.filter(
                    distribution=distribution, component=component, codename="", suite=""
                )
                package = content_to_add[0]
                release_arch = ReleaseArchitecture(
                    distribution=distribution, architecture=package.architecture
                )
                release_arch.save()
                release_arch_to_add = ReleaseArchitecture.objects.filter(
                    distribution=distribution, architecture=package.architecture
                )
                package_release = PackageReleaseComponent(
                    release_component=release_component, package=package
                )
                package_release.save()
                package_release_to_add = PackageReleaseComponent.objects.filter(
                    release_component=release_component, package=package
                )

                with repository.new_version() as new_version:
                    new_version.add_content(content_to_add)
                    new_version.add_content(release_component_to_add)
                    new_version.add_content(release_arch_to_add)
                    new_version.add_content(package_release_to_add)

            return result

        result = super().create(validated_data)
        return result

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = SingleArtifactContentUploadSerializer.Meta.fields + ("distribution", "component")


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
        if "essential" in package_fields:
            package_fields["essential"] = package_fields["essentials"].lower()
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


class BasePackageMixin(Serializer):
    """
    A Mixin Serializer for abstract BasePackage fields.
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

        return data

    def retrieve(self, validated_data):
        content = self.Meta.model.objects.filter(
            sha256=validated_data["sha256"], relative_path=validated_data["relative_path"]
        )

        return content.first()

    class Meta:
        fields = (
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


class PackageSerializer(BasePackageMixin, SinglePackageUploadSerializer, ContentChecksumSerializer):
    """
    A Serializer for Package.
    """

    def deferred_validate(self, data):
        """Validate for 'normal' Package (not installer)."""
        data = super().deferred_validate(data)

        if data.get("section") == "debian-installer":
            raise ValidationError(_("Not a valid Deb Package"))

        return data

    class Meta(SinglePackageUploadSerializer.Meta):
        fields = (
            SinglePackageUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
            + BasePackageMixin.Meta.fields
        )
        model = Package
        from822_serializer = Package822Serializer


class InstallerPackageSerializer(
    BasePackageMixin, SingleArtifactContentUploadSerializer, ContentChecksumSerializer
):
    """
    A Serializer for InstallerPackage.
    """

    def deferred_validate(self, data):
        """Validate for InstallerPackage."""
        data = super().deferred_validate(data)

        if data.get("section") != "debian-installer":
            raise ValidationError(_("Not a valid uDeb Package"))

        return data

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
            + BasePackageMixin.Meta.fields
        )
        model = InstallerPackage
        from822_serializer = InstallerPackage822Serializer


class ReleaseSerializer(NoArtifactContentSerializer):
    """
    A Serializer for Release.
    """

    codename = CharField()
    suite = CharField()
    distribution = CharField()
    version = NullableCharField(required=False, allow_null=True, default=None)
    origin = NullableCharField(required=False, allow_null=True, default=None)
    label = NullableCharField(required=False, allow_null=True, default=None)
    description = NullableCharField(required=False, allow_null=True, default=None)

    class Meta(NoArtifactContentSerializer.Meta):
        model = Release
        fields = NoArtifactContentSerializer.Meta.fields + (
            "codename",
            "suite",
            "distribution",
            "version",
            "origin",
            "label",
            "description",
        )


class ReleaseArchitectureSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseArchitecture.
    """

    architecture = CharField(help_text="Name of the architecture.")
    distribution = CharField(help_text="Name of the distribution.")

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseArchitecture
        fields = NoArtifactContentSerializer.Meta.fields + (
            "architecture",
            "distribution",
            "codename",
            "suite",
        )


class ReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseComponent.
    """

    component = CharField(help_text="Name of the component.")
    distribution = CharField(help_text="Name of the distribution.")

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + (
            "component",
            "distribution",
            "codename",
            "suite",
        )


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
