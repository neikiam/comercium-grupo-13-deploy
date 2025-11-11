from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_tag
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("allauth.urls")),
    path("market/", include("mercado.urls")),
    path("profiles/", include("perfil.urls")),
    path("user-activity/", include("user_activity.urls")),
    path("chat/", include("chat_interno.urls")),
    path("notifications/", include("notifications.urls")),
    path("favicon.ico", RedirectView.as_view(url=static_tag('favicon.svg'), permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if not settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
