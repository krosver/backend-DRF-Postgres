from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("api/rbac/", include("rbac.urls")),
    path("api/users/", include("users.urls")),
    path("api/biz/",include('biz.urls')),
]
