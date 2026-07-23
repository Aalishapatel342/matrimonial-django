from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include

urlpatterns = [
    # Silently handle favicon.ico requests (browsers auto-request this)
    path("favicon.ico", lambda r: HttpResponse(status=204)),
    path("", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    if hasattr(settings, "MEDIA_ROOT") and settings.MEDIA_ROOT:
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

