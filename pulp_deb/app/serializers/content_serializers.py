from gettext import gettext as _

import os
from django.conf import settings

from debian import deb822, debfile

from rest_framework.serializers import CharField, DictField, Field, ValidationError, Serializer
from pulpcore.plugin.models import Artifact, CreatedResource, RemoteArtifact
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    NoArtifactContentSerializer,
    SingleArtifactContentSerializer,
    SingleArtifactContentUploadSerializer,
    DetailRelatedField,
    SingleContentArtifactField,
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
    SourceIndex,
    SourcePackage,
    SourcePackageReleaseComponent,
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


class SourceIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for SourceIndex.
    """

    component = CharField(help_text="Component this index file belongs to.", required=True)

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
            "relative_path",
        )
        model = SourceIndex


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

    @staticmethod
    def _get_or_create_content_and_qs(model, **data):
        content, created = model.objects.get_or_create(**data)
        if created:
            CreatedResource(content_object=content).save()
        return content, model.objects.filter(pk=content.pk)

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
            repository = validated_data.pop("repository")
            repository.cast()

            package = super().create(validated_data)
            package_qs = self.Meta.model.objects.filter(pk=package.pk)

            message = _('Adding uploaded package "{}" to component "{}" of distribution "{}".')
            log.info(message.format(package.name, component, distribution))

            component, component_qs = self._get_or_create_content_and_qs(
                ReleaseComponent, distribution=distribution, component=component
            )
            architecture_qs = self._get_or_create_content_and_qs(
                ReleaseArchitecture, distribution=distribution, architecture=package.architecture
            )[1]
            prc_qs = self._get_or_create_content_and_qs(
                PackageReleaseComponent, release_component=component, package=package
            )[1]

            with repository.new_version() as new_version:
                new_version.add_content(package_qs)
                new_version.add_content(component_qs)
                new_version.add_content(architecture_qs)
                new_version.add_content(prc_qs)
        else:
            package = super().create(validated_data)

        return package

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


class SourceSha1Serializer(Serializer):
    """
    A Serializer for Checksums-Sha1 list.
    """

    name = CharField()
    size = CharField()
    sha1 = CharField(max_length=40)

    class Meta:
        fields = (
            "sha1",
            "size",
            "name",
        )


class SourceSha256Serializer(Serializer):
    """
    A Serializer for Checksums-Sha256 list.
    """

    name = CharField(required=True)
    size = CharField(required=True)
    sha256 = CharField(max_length=64)

    class Meta:
        fields = (
            "sha256",
            "size",
            "name",
        )


class SourceSha512Serializer(Serializer):
    """
    A Serializer for Checksums-Sha512 list.
    """

    name = CharField()
    size = CharField()
    sha512 = CharField(max_length=128)

    class Meta:
        fields = (
            "sha512",
            "size",
            "name",
        )


class SourceMd5sumSerializer(Serializer):
    """
    A Serializer for Files list.
    """

    name = CharField()
    size = CharField()
    md5sum = CharField(max_length=32)

    class Meta:
        fields = (
            "md5sum",
            "size",
            "name",
        )


class DscFile822Serializer(NoArtifactContentSerializer):
    """
    A Serializer for DscFile used for conversion to/from 822 format.
    """

    TRANSLATION_DICT = {
        "format": "Format",
        "source": "Source",
        "binary": "Binary",
        "architecture": "Architecture",
        "version": "Version",
        "maintainer": "Maintainer",
        "uploaders": "Uploaders",
        "homepage": "Homepage",
        "vcs_browser": "Vcs-Browser",
        "vcs_arch": "Vcs-Arch",
        "vcs_bzr": "Vcs-Bzr",
        "vcs_cvs": "Vcs-Cvs",
        "vcs_darcs": "Vcs-Darcs",
        "vcs_git": "Vcs-Git",
        "vcs_hg": "Vcs-Hg",
        "vcs_mtn": "Vcs-Mtn",
        "vcs_snv": "Vcs-Svn",
        "testsuite": "Testsuite",
        "dgit": "Dgit",
        "standards_version": "Standards-Version",
        "build_depends": "Build-Depends",
        "build_depends_indep": "Build-Depends-Indep",
        "build_depends_arch": "Build-Depends-Arch",
        "build_conflicts": "Build-Conflicts",
        "build_conflicts_indep": "Build-Conflicts-Indep",
        "build_conflicts_arch": "Build-Conflicts-Arch",
        "package_list": "Package-List",
        "checksums_sha1": "Checksums-Sha1",
        "checksums_sha256": "Checksums-Sha256",
        "checksums_sha512": "Checksums-Sha512",
        "files": "Files",
    }

    format = CharField()
    source = CharField()
    binary = CharField(required=False)
    architecture = CharField(required=False)
    version = CharField()
    maintainer = CharField()
    uploaders = CharField(required=False)
    homepage = CharField(required=False)
    vcs_browser = CharField(required=False)
    vcs_arch = CharField(required=False)
    vcs_bzr = CharField(required=False)
    vcs_cvs = CharField(required=False)
    vcs_darcs = CharField(required=False)
    vcs_git = CharField(required=False)
    vcs_hg = CharField(required=False)
    vcs_mtn = CharField(required=False)
    vcs_snv = CharField(required=False)
    testsuite = CharField(required=False)
    dgit = CharField(required=False)
    standards_version = CharField()
    build_depends = CharField(required=False)
    build_depends_indep = CharField(required=False)
    build_depends_arch = CharField(required=False)
    build_conflicts = CharField(required=False)
    build_conflicts_indep = CharField(required=False)
    build_conflicts_arch = CharField(required=False)
    package_list = CharField(required=False)
    checksums_sha1 = SourceSha1Serializer(many=True, required=False)
    checksums_sha256 = SourceSha256Serializer(many=True)
    checksums_sha512 = SourceSha512Serializer(many=True, required=False)
    files = SourceMd5sumSerializer(many=True)

    @classmethod
    def from822(cls, data, **kwargs):
        """
        Translate deb822.Dsc to a dictionary for class instatiation. Automatically determines if
        the incoming data is from a sources index paragraph and adjusts accordingly.
        """
        if "Directory" in data and "Package" in data:
            data["Source"] = data.pop("Package")
            data.pop("Directory")
            if "Priority" in data:
                data.pop("Priority")
            if "Section" in data:
                data.pop("Section")

        return cls(
            data={k: data[v] for k, v in cls.TRANSLATION_DICT.items() if v in data}, **kwargs
        )

    def to822(self, component="", paragraph=False):
        """
        Create deb822.Dsc object from model. If the 'paragraph' argument is True then the returned
        object will be adjusted to be a valid paragraph in a source index file.
        """
        ret = deb822.Dsc()

        # Respect ALLOWED_CONTENT_CHECKSUMS
        all_checksums = {
            "sha1": "checksums_sha1",
            "sha256": "checksums_sha256",
            "sha512": "checksums_sha512",
            "md5": "files",
        }
        disallowed_checksums = {
            k: all_checksums[k]
            for k, v in all_checksums.items()
            if k not in settings.ALLOWED_CONTENT_CHECKSUMS
        }

        for k, v in self.TRANSLATION_DICT.items():
            if k in disallowed_checksums.values():
                continue
            value = self.data.get(k)
            if value:
                ret[v] = value

        # DB storage strips leading newline-space from the first 'Package-List' entry, restore it.
        if "Package-List" in ret and ret["Package-List"][0] != "\n":
            ret["Package-List"] = "\n {}".format(ret["Package-List"])

        if paragraph:
            """
            Used as a paragraph in the Sources indices file. Use 'Package' instead of 'Source'
            and include 'Directory'. Currently we skip the optional 'Priority' and 'Section'.
            """
            ret["Package"] = ret.pop("Source")
            ret["Directory"] = self.instance.derived_dir(component)

        return ret

    class Meta:
        fields = (
            "format",
            "source",
            "binary",
            "architecture",
            "version",
            "maintainer",
            "uploaders",
            "homepage",
            "vcs_browser",
            "vcs_arch",
            "vcs_bzr",
            "vcs_cvs",
            "vcs_darcs",
            "vcs_git",
            "vcs_hg",
            "vcs_mtn",
            "vcs_snv",
            "testsuite",
            "dgit",
            "standards_version",
            "build_depends",
            "build_depends_indep",
            "build_depends_arch",
            "build_conflicts",
            "build_conflicts_indep",
            "build_conflicts_arch",
            "package_list",
            "checksums_sha1",
            "checksums_sha256",
            "checksums_sha512",
            "files",
        )
        model = SourcePackage


class SourcePackageSerializer(MultipleArtifactContentSerializer):
    """
    A Serializer for DscFile.
    """

    artifact = SingleContentArtifactField(
        help_text=_("Artifact URL of the Debian Source Control (dsc) file."),
        write_only=True,
    )
    relative_path = CharField(
        help_text=_(
            "Relative path of the Debian Source Control (dsc) file."
            "It is normally advised to let Pulp generate this."
        ),
        required=False,
    )
    format = CharField(read_only=True)
    source = CharField(read_only=True)
    binary = CharField(read_only=True)
    architecture = CharField(read_only=True)
    version = CharField(read_only=True)
    maintainer = CharField(read_only=True)
    uploaders = CharField(read_only=True)
    homepage = CharField(read_only=True)
    vcs_browser = CharField(read_only=True)
    vcs_arch = CharField(read_only=True)
    vcs_bzr = CharField(read_only=True)
    vcs_cvs = CharField(read_only=True)
    vcs_darcs = CharField(read_only=True)
    vcs_git = CharField(read_only=True)
    vcs_hg = CharField(read_only=True)
    vcs_mtn = CharField(read_only=True)
    vcs_snv = CharField(read_only=True)
    testsuite = CharField(read_only=True)
    dgit = CharField(read_only=True)
    standards_version = CharField(read_only=True)
    build_depends = CharField(read_only=True)
    build_depends_indep = CharField(read_only=True)
    build_depends_arch = CharField(read_only=True)
    build_conflicts = CharField(read_only=True)
    build_conflicts_indep = CharField(read_only=True)
    build_conflicts_arch = CharField(read_only=True)
    package_list = CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        """Initializer for DscFileSerializer."""
        super().__init__(*args, **kwargs)
        self.fields["artifacts"].read_only = True

    def create(self, validated_data):
        """Create DscFileSerializer"""
        skip_keys = ["artifact", "files", "checksums_sha1", "checksums_sha256", "checksums_sha512"]
        return super().create({k: validated_data[k] for k in validated_data if k not in skip_keys})

    def validate(self, data):
        """Validate that DscFile data."""
        data = super().validate(data)

        if "request" not in self.context:
            data = self.deferred_validate(data)
        return data

    def deferred_validate(self, data):
        """Validate that the artifact is a source control file and extract it's values."""
        try:
            source_paragraph = deb822.Dsc(data["artifact"].file)
        except Exception:  # TODO: Be more specific
            raise ValidationError(_("Unable to read Source Control File"))

        from822_serializer = DscFile822Serializer.from822(data=source_paragraph)
        from822_serializer.is_valid(raise_exception=True)
        source_data = from822_serializer.validated_data
        data.update(source_data)

        """
        Really no leeway here. 'name' and 'filename' must match contents of DSC
        only the path component of relative_path can be adjusted (though shouldn't)
        """
        model = self.Meta.model(**source_data)
        if "relative_path" not in data:
            data["relative_path"] = model.derived_path(model.derived_dsc_filename())
        elif not os.path.basename(data["relative_path"]) == model.derived_dsc_filename():
            raise ValidationError(
                _("Invalid relative_path provided '{}', filename '{}' do not match.").format(
                    data["relative_path"], model.derived_dsc_filename()
                )
            )

        content = SourcePackage.objects.filter(source=data["source"], version=data["version"])
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a DSC file with version '{version}' and source name "
                    "'{source}'."
                ).format(version=data["version"], source=data["source"])
            )

        artifacts = {data["relative_path"]: data["artifact"]}
        for source in data["checksums_sha256"]:
            content = Artifact.objects.filter(sha256=source["sha256"], size=source["size"])
            if not content.exists():
                raise ValidationError(
                    _(
                        "A source file is listed in the DSC file but is not yet available '{name}'"
                        " and sha256 '{sha256}'."
                    ).format(name=source["name"], sha256=source["sha256"])
                )
            artifacts[
                os.path.join(os.path.dirname(data["relative_path"]), source["name"])
            ] = content.first()

        data["artifacts"] = artifacts
        return data

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "artifact",
            "relative_path",
            "format",
            "source",
            "binary",
            "architecture",
            "version",
            "maintainer",
            "uploaders",
            "homepage",
            "vcs_browser",
            "vcs_arch",
            "vcs_bzr",
            "vcs_cvs",
            "vcs_darcs",
            "vcs_git",
            "vcs_hg",
            "vcs_mtn",
            "vcs_snv",
            "testsuite",
            "dgit",
            "standards_version",
            "build_depends",
            "build_depends_indep",
            "build_depends_arch",
            "build_conflicts",
            "build_conflicts_indep",
            "build_conflicts_arch",
            "package_list",
        )
        model = SourcePackage


class SourcePackageReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for SourcePackageReleaseComponent.
    """

    source_package = DetailRelatedField(
        help_text="Source package that is contained in release_component.",
        many=False,
        queryset=SourcePackage.objects.all(),
        view_name="deb-souce_package_component-detail",
    )
    release_component = DetailRelatedField(
        help_text="ReleaseComponent this source package is contained in.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-release_component-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = SourcePackageReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("source_package", "release_component")
