from django.conf.urls import url

from .viewsets import OneShotUploadViewSet


urlpatterns = [url(r"deb/upload/$", OneShotUploadViewSet.as_view({"post": "create"}))]
