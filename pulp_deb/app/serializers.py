from rest_framework import serializers
from pulpcore.plugin import serializers as platform

from . import models


class YesNoField(serializers.Field):
    """
    A serializer field that accepts 'yes' or 'no' as boolean.
    """
    def to_representation(self, value):
        if value == True:
            return 'yes'
        elif value == False:
            return 'no'

    def to_internal_value(self, data):
        data = data.strip().lower()
        if data == 'yes':
            return True
        if data == 'no':
            return False
        else:
            raise serializers.ValidationError('Value must be "yes" or "no".')


class GenericContentSerializer(platform.SingleArtifactContentSerializer):
    """
    A serializer for GenericContent.
    """

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + ('relative_path',)
        model = models.GenericContent


class ReleaseSerializer(platform.MultipleArtifactContentSerializer):
    """
    A serializer for Release.
    """

    codename = serializers.CharField(
        help_text='Codename of the release, i.e. "buster".',
        required=True,
    )

    suite = serializers.CharField(
        help_text='Suite of the release, i.e. "stable".',
        required=False,
    )

    distribution = serializers.CharField(
        help_text='Distribution of the release, i.e. "stable/updates".',
        required=False,
    )

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.MultipleArtifactContentSerializer.Meta.fields \
            + ('codename', 'suite', 'distribution', 'relative_path',)
        model = models.GenericContent


class PackageIndexSerializer(platform.MultipleArtifactContentSerializer):
    """
    A serializer for PackageIndex.
    """

    component = serializers.CharField(
        help_text='Component of the component - architecture combination.',
        required=True,
    )

    architecture = serializers.CharField(
        help_text='Architecture of the component - architecture combination.',
        required=True,
    )

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.MultipleArtifactContentSerializer.Meta.fields + \
            ('release', 'component', 'architecture', 'relative_path')
        model = models.PackageIndex


class InstallerFileIndexSerializer(platform.MultipleArtifactContentSerializer):
    """
    A serializer for InstallerFileIndex.
    """

    component = serializers.CharField(
        help_text='Component of the component - architecture combination.',
        required=True,
    )

    architecture = serializers.CharField(
        help_text='Architecture of the component - architecture combination.',
        required=True,
    )

    relative_path = serializers.CharField(
        help_text='Path of directory containing MD5SUMS and SHA256SUMS relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.MultipleArtifactContentSerializer.Meta.fields + \
            ('release', 'component', 'architecture', 'relative_path')
        model = models.InstallerFileIndex


class PackageSerializer(platform.SingleArtifactContentSerializer):
    """
    A Serializer for Package.
    """

    essential = YesNoField(
        required=False,
    )

    build_essential = YesNoField(
        required=False,
    )

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            'package_name',
            'source',
            'version',
            'architecture',
            'section',
            'priority',
            'origin',
            'tag',
            'bugs',
            'essential',
            'build_essential',
            'installed_size',
            'maintainer',
            'original_maintainer',
            'description',
            'description_md5',
            'homepage',
            'built_using',
            'auto_built_package',
            'multi_arch',
            'breaks',
            'conflicts',
            'depends',
            'recommends',
            'suggests',
            'enhances',
            'pre_depends',
            'provides',
            'replaces',
            'relative_path',
            'sha256',
        )
        model = models.Package


class InstallerPackageSerializer(platform.SingleArtifactContentSerializer):
    """
    A Serializer for InstallerPackage.
    """

    essential = YesNoField(
        required=False,
    )

    build_essential = YesNoField(
        required=False,
    )

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            'package_name',
            'source',
            'version',
            'architecture',
            'section',
            'priority',
            'origin',
            'tag',
            'bugs',
            'essential',
            'build_essential',
            'installed_size',
            'maintainer',
            'original_maintainer',
            'description',
            'description_md5',
            'homepage',
            'built_using',
            'auto_built_package',
            'multi_arch',
            'breaks',
            'conflicts',
            'depends',
            'recommends',
            'suggests',
            'enhances',
            'pre_depends',
            'provides',
            'replaces',
            'relative_path',
            'sha256',
        )
        model = models.InstallerPackage


class DebRemoteSerializer(platform.RemoteSerializer):
    """
    A Serializer for DebRemote.
    """

    distributions = serializers.CharField(
        help_text='Whitespace separated list of distributions to sync',
        required=True,
    )

    components = serializers.CharField(
        help_text='Whitespace separatet list of components to sync',
        required=False,
    )

    architectures = serializers.CharField(
        help_text='Whitespace separated list of architectures to sync',
        required=False,
    )

    sync_sources = serializers.BooleanField(
        help_text='Sync source packages',
        required=False,
    )

    sync_udebs = serializers.BooleanField(
        help_text='Sync installer packages',
        required=False,
    )

    sync_installer = serializers.BooleanField(
        help_text='Sync installer files',
        required=False,
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + (
            'distributions',
            'components',
            'architectures',
            'sync_sources',
            'sync_udebs',
            'sync_installer',
        )
        model = models.DebRemote


class DebVerbatimPublisherSerializer(platform.PublisherSerializer):
    """
    A Serializer for DebVerbatimPublisher.
    """

    class Meta:
        fields = platform.PublisherSerializer.Meta.fields
        model = models.DebVerbatimPublisher


class DebPublisherSerializer(platform.PublisherSerializer):
    """
    A Serializer for DebPublisher.
    """

    simple = serializers.BooleanField(
        help_text='Activate simple publishing mode (all packages in one release component).',
        default=False,
    )
    structured = serializers.BooleanField(
        help_text='Activate structured publishing mode.',
        default=False,
    )

    def validate(self, data):
        """
        Check that the publishing modes are compatible.
        """
        if not data['simple'] and not data['structured']:
            raise serializers.ValidationError(
                "one of simple or structured publishing mode must be selected")
        return data

    class Meta:
        fields = platform.PublisherSerializer.Meta.fields + (
            'simple',
            'structured',
        )
        model = models.DebPublisher
