from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('accounts/', include('allauth.urls')),
    path('projects/', include('project_profiling.urls')),
]
