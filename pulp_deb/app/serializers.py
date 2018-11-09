from rest_framework import serializers

from pulpcore.plugin.serializers import (
    ContentSerializer,
    RelatedField,
    RemoteSerializer,
    PublisherSerializer
)

from . import models


class GenericContentSerializer(ContentSerializer):
    """
    A serializer for GenericContent.
    """

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = tuple(set(ContentSerializer.Meta.fields) - {'artifacts'}) + ('relative_path',
                                                                              'artifact')
        model = models.GenericContent


class ReleaseSerializer(ContentSerializer):
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
        fields = tuple(set(ContentSerializer.Meta.fields) -
                       {'artifacts'}) + ('codename', 'suite', 'distribution', 'relative_path', 'artifact')
        model = models.GenericContent


class PackageIndexSerializer(ContentSerializer):
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
        fields = ContentSerializer.Meta.fields + \
            ('release', 'component', 'architecture', 'relative_path')
        model = models.PackageIndex


class PackageSerializer(ContentSerializer):
    """
    A Serializer for Package.
    """

    relative_path = serializers.CharField(
        help_text='Path of file relative to url.',
        required=False,
    )

    class Meta:
        fields = tuple(set(ContentSerializer.Meta.fields) - {'artifacts'}) + (
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


class DebRemoteSerializer(RemoteSerializer):
    """
    A Serializer for DebRemote.
    """

    distributions = serializers.CharField(
        help_text='Comma separated list of distributions to sync',
        required=True,
    )
    components = serializers.CharField(
        help_text='Comma separatet list of components to sync',
        required=False,
    )
    architectures = serializers.CharField(
        help_text='Comma separated list of architectures to sync',
        required=False,
    )

    class Meta:
        fields = RemoteSerializer.Meta.fields + \
            ('distributions', 'components', 'architectures')
        model = models.DebRemote


class DebPublisherSerializer(PublisherSerializer):
    """
    A Serializer for DebPublisher.
    """

    verbatim = serializers.BooleanField(
        help_text='Publish upstream repository verbatim. Works only with synched content.',
        required=False,
        default=False,
    )
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
        if data['verbatim']:
            if data['simple'] or data['structured']:
                raise serializers.ValidationError("verbatim publishing mode cannot combined with simple or structured")
        else:
            if not data['simple'] and not data['structured']:
                raise serializers.ValidationError("one of verbatim, simple or structured publishing mode must be selected")
        return data

    class Meta:
        fields = PublisherSerializer.Meta.fields + (
            'verbatim',
            'simple',
            'structured',
        )
        model = models.DebPublisher
