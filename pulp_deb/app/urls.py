# This file is modeled after the corresponding file from pulp_rpm.
# If there are problems with the copy API, or domain support should be added, consult pulp_rpm.

from django.conf import settings
from django.urls import path

from .viewsets import CopyViewSet

V3_API_ROOT = settings.V3_API_ROOT_NO_FRONT_SLASH

urlpatterns = [
    path(f"{V3_API_ROOT}deb/copy/", CopyViewSet.as_view({"post": "create"})),
]
