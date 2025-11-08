"""
Comando de management para limpiar carritos abandonados.

Uso:
    python manage.py cleanup_abandoned_carts
    python manage.py cleanup_abandoned_carts --days 45
    python manage.py cleanup_abandoned_carts --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mercado.models import Cart, CartItem


class Command(BaseCommand):
    help = 'Limpia carritos abandonados que no han sido actualizados en X días'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de días de inactividad para considerar un carrito abandonado (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué carritos se eliminarían sin eliminarlos realmente'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff = timezone.now() - timedelta(days=days)
        old_carts = Cart.objects.filter(updated_at__lt=cutoff)
        total_items = sum(cart.items.count() for cart in old_carts)
        total_carts = old_carts.count()
        
        if total_carts == 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ No hay carritos abandonados (más de {days} días sin actividad)')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Se eliminarían:')
            )
            self.stdout.write(f'  - {total_carts} carritos abandonados')
            self.stdout.write(f'  - {total_items} items en total')
            self.stdout.write(f'  - Carritos sin actividad desde: {cutoff.strftime("%Y-%m-%d %H:%M:%S")}')
            
            if total_carts > 0:
                self.stdout.write(f'\nEjemplos de carritos a eliminar:')
                for cart in old_carts[:5]:
                    self.stdout.write(
                        f'  - Usuario: {cart.user.username}, '
                        f'Items: {cart.items.count()}, '
                        f'Última actualización: {cart.updated_at.strftime("%Y-%m-%d")}'
                    )
                if total_carts > 5:
                    self.stdout.write(f'  ... y {total_carts - 5} más')
        else:
            deleted_count = old_carts.delete()[0]
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Limpieza completada:')
            )
            self.stdout.write(f'  - {deleted_count} registros eliminados')
            self.stdout.write(f'  - {total_carts} carritos antiguos')
            self.stdout.write(f'  - {total_items} items liberados')
            self.stdout.write(f'  - Inactivos desde: {cutoff.strftime("%Y-%m-%d")}')
            
        if not dry_run:
            self.stdout.write(
                self.style.MIGRATE_HEADING('\n💡 Sugerencia:')
            )
            self.stdout.write(
                'Puedes automatizar esta limpieza con cron o celery beat.\n'
                'Ejemplo cron (semanal): 0 2 * * 0 python manage.py cleanup_abandoned_carts'
            )
