# This file is modeled after the corresponding file from pulp_rpm.
# If there are problems with the copy API, or domain support should be added, consult pulp_rpm.

from django.conf import settings
from django.urls import path

from pulpcore.plugin.find_url import find_api_root

from .viewsets import CopyViewSet

if getattr(settings, "ENABLE_V4_API", None):
    VERSION = "<str:version>"
else:
    VERSION = "v3"

_, API_ROOT = find_api_root(lstrip=True, version=VERSION)

urlpatterns = [
    path(f"{API_ROOT}deb/copy/", CopyViewSet.as_view({"post": "create"})),
]
