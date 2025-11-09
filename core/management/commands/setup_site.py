"""
Comando para configurar el sitio de Django para allauth/OAuth.
"""
import os

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Configura el sitio de Django para allauth/OAuth basado en el hostname de Render'

    def handle(self, *args, **options):
        # Obtener el hostname desde variables de entorno
        render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
        
        if not render_hostname:
            self.stdout.write(
                self.style.WARNING(
                    'RENDER_EXTERNAL_HOSTNAME no encontrada. '
                    'Usando configuración local (127.0.0.1:8000)'
                )
            )
            domain = '127.0.0.1:8000'
            name = 'Comercium Local'
        else:
            domain = render_hostname
            name = 'Comercium'
        
        try:
            # Obtener o crear el sitio con SITE_ID=1
            site = Site.objects.get(pk=1)
            site.domain = domain
            site.name = name
            site.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Sitio configurado correctamente:\n'
                    f'  Domain: {domain}\n'
                    f'  Name: {name}'
                )
            )
        except Site.DoesNotExist:
            site = Site.objects.create(pk=1, domain=domain, name=name)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Sitio creado correctamente:\n'
                    f'  Domain: {domain}\n'
                    f'  Name: {name}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error al configurar el sitio: {e}')
            )
