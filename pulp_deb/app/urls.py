# This file is modeled after the corresponding file from pulp_rpm.
# If there are problems with the copy API, or domain support should be added, consult pulp_rpm.

from django.conf import settings
from django.urls import path, include

from .viewsets import CopyViewSet

if settings.DOMAIN_ENABLED:
    V3_API_ROOT = settings.V3_DOMAIN_API_ROOT_NO_FRONT_SLASH
else:
    V3_API_ROOT = settings.V3_API_ROOT_NO_FRONT_SLASH

additional_deb_apis = [
    path("copy/", CopyViewSet.as_view({"post": "create"})),
]

urlpatterns = [
    path(f"{V3_API_ROOT}deb/", include(additional_deb_apis)),
]

if getattr(settings, "ENABLE_V4_API", False):
    V4_API_ROOT = settings.V4_DOMAIN_API_ROOT_NO_FRONT_SLASH

    additional_deb_apis = [
        path("copy/", CopyViewSet.as_view({"post": "create"}, name="deb-copy")),
    ]

    path(f"{V4_API_ROOT}rpm/", include((additional_deb_apis, "deb"), namespace="v4"))
