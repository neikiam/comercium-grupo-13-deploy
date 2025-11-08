from django.apps import AppConfig
from django.dispatch import receiver

try:
    # Import opcional: disponible cuando Django está listo
    from django.db.backends.signals import connection_created
except Exception:
    connection_created = None


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Configuraciones específicas para SQLite para reducir locks en desarrollo
        if connection_created is not None:
            @receiver(connection_created)
            def configure_sqlite(sender, connection, **kwargs):
                if getattr(connection, 'vendor', None) == 'sqlite':
                    try:
                        cursor = connection.cursor()
                        cursor.execute("PRAGMA journal_mode=WAL;")
                        # Sincronización NORMAL para mejor rendimiento en dev
                        cursor.execute("PRAGMA synchronous=NORMAL;")
                        cursor.execute("PRAGMA foreign_keys=ON;")
                    except Exception:
                        pass
