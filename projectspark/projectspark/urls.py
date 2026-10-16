"""
URL configuration for projectspark project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('appspark.urls')),

    # Serves uploaded files (profile pictures etc.). This is wired up by hand
    # instead of with django.conf.urls.static.static(), because that helper
    # returns an empty list whenever DEBUG is False - so with DEBUG=False every
    # /media/ URL 404s and uploaded profile pictures silently disappear.
    # WhiteNoise doesn't cover this either: it only serves STATIC_ROOT, not
    # user uploads. Django's docs recommend a dedicated storage service (S3,
    # etc.) for real production - for a project at this scale, serving media
    # directly like this is a reasonable trade-off over adding a whole separate
    # storage service, but it's worth knowing this isn't the "textbook" setup.
    re_path(
        r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')),
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
