from django.apps import AppConfig


class MercadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mercado'

    def ready(self):
        """Importa señales cuando la app está lista."""
        import mercado.signals
