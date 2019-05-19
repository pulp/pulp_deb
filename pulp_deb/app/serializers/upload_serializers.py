from gettext import gettext as _

from rest_framework.serializers import FileField, HyperlinkedRelatedField, Serializer
from pulpcore.plugin.models import Artifact, Repository


class OneShotUploadSerializer(Serializer):
    """
    A serializer for the One Shot Upload API.
    """

    repository = HyperlinkedRelatedField(
        help_text=_("A URI of the repository."),
        required=False,
        queryset=Repository.objects.all(),
        view_name="repositories-detail",
    )
    file = FileField(help_text=_("The deb file."), required=True)

    def validate(self, data):
        """
        Validate uploaded file, prepare artifact and collect shared resources.
        """
        data = super().validate(data)
        data["filename"] = data["file"].name
        data["artifact"] = Artifact.init_and_validate(data["file"])
        return data
