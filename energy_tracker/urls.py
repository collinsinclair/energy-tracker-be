from django.contrib import admin
from django.urls import include, path
from energy import urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("energy/", include(urls)),
]
