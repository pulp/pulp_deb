from django.urls import path

from .viewsets import CopyViewSet

urlpatterns = [path("pulp/api/v3/deb/copy/", CopyViewSet.as_view({"post": "create"}))]
