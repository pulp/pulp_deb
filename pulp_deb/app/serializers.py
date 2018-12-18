from rest_framework import serializers
from pulpcore.plugin import serializers as platform

from . import models


class GenericContentSerializer(platform.ContentSerializer):
    """
    A serializer for GenericContent.
    """

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = tuple(set(platform.ContentSerializer.Meta.fields) - {'artifacts'}) + (
            'relative_path',
            'artifact',
        )
        model = models.GenericContent


class ReleaseSerializer(platform.ContentSerializer):
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
        fields = tuple(set(platform.ContentSerializer.Meta.fields) - {'artifacts'}) \
            + ('codename', 'suite', 'distribution', 'relative_path', 'artifact')
        model = models.GenericContent


class PackageIndexSerializer(platform.ContentSerializer):
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
        fields = platform.ContentSerializer.Meta.fields + \
            ('release', 'component', 'architecture', 'relative_path')
        model = models.PackageIndex


class PackageSerializer(platform.ContentSerializer):
    """
    A Serializer for Package.
    """

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = tuple(set(platform.ContentSerializer.Meta.fields) - {'artifacts'}) + (
            'relative_path',
            'artifact',
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
        )
        model = models.Package


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

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + \
            ('distributions', 'components', 'architectures')
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
