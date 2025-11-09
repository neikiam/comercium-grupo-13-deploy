"""Context processors para el proyecto."""
from django.conf import settings


def socialaccount_settings(request):
    """Proporciona configuraciones de redes sociales al contexto de templates."""
    return {
        'GOOGLE_CLIENT_ID': getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id'),
    }
