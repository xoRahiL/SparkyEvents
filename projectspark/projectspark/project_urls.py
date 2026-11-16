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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('appspark.urls')),
]

# Serves uploaded files (profile pictures etc.) regardless of DEBUG.
# Django's docs recommend a dedicated storage service (S3, etc.) for real
# production - for a project at this scale, serving media directly like
# this is a reasonable trade-off over adding a whole separate storage
# service, but it's worth knowing this isn't the "textbook" production setup.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)