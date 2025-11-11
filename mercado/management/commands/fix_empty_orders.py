"""
Comando para corregir órdenes que no tienen items.
Uso: python manage.py fix_empty_orders
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from mercado.models import Order, OrderItem


class Command(BaseCommand):
    help = 'Identifica y elimina órdenes vacías (sin items)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Eliminar órdenes vacías en lugar de solo listarlas',
        )

    def handle(self, *args, **options):
        # Encontrar órdenes sin items
        empty_orders = Order.objects.annotate(
            items_count=models.Count('items')
        ).filter(items_count=0)

        if not empty_orders.exists():
            self.stdout.write(self.style.SUCCESS('✓ No hay órdenes vacías'))
            return

        self.stdout.write(f'\n⚠ Encontradas {empty_orders.count()} órdenes vacías:\n')
        
        for order in empty_orders:
            self.stdout.write(
                f'  - Orden #{order.id}: '
                f'Comprador={order.buyer}, '
                f'Total=${order.total}, '
                f'Payment ID={order.payment_id}'
            )

        if options['delete']:
            with transaction.atomic():
                deleted_count, _ = empty_orders.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ {deleted_count} órdenes vacías eliminadas')
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ Para eliminarlas, ejecuta: python manage.py fix_empty_orders --delete'
                )
            )
