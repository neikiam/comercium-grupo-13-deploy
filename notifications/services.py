import logging

from django.db import transaction

from notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio para crear notificaciones de forma centralizada."""
    
    @staticmethod
    def create_sale_notification(seller, order):
        """Notifica al vendedor sobre una nueva venta."""
        items_sold = order.items.filter(seller=seller)
        if not items_sold.exists():
            return
        
        total_vendido = sum(item.subtotal() for item in items_sold)
        count = items_sold.count()
        
        Notification.objects.create(
            recipient=seller,
            notification_type=Notification.TYPE_NEW_SALE,
            title=f"¡Nueva venta! {count} producto(s)",
            message=f"Has vendido {count} producto(s) por un total de ${total_vendido}. Orden #{order.id}",
            link=f"/mercado/mis-ventas/",
            related_order_id=order.id,
            related_user=order.buyer
        )
    
    @staticmethod
    def create_follower_notification(follower, following):
        """Notifica cuando alguien te empieza a seguir."""
        Notification.objects.create(
            recipient=following,
            notification_type=Notification.TYPE_NEW_FOLLOWER,
            title="Nuevo seguidor",
            message=f"{follower.username} comenzó a seguirte",
            link=f"/profiles/usuario/{follower.id}/",
            related_user=follower
        )
    
    @staticmethod
    def create_new_product_notification(product):
        """Notifica a los seguidores cuando publicas un nuevo producto."""
        from notifications.models import Follow
        
        followers = Follow.objects.filter(following=product.seller).select_related('follower')
        
        notifications = [
            Notification(
                recipient=follow.follower,
                notification_type=Notification.TYPE_NEW_PRODUCT,
                title=f"{product.seller.username} publicó un nuevo producto",
                message=f"{product.title} - ${product.price}",
                link=f"/market/detail/{product.id}/",
                related_product_id=product.id,
                related_user=product.seller
            )
            for follow in followers
        ]
        
        if notifications:
            Notification.objects.bulk_create(notifications)
            logger.info(f"Creadas {len(notifications)} notificaciones para nuevo producto #{product.id}")
    
    @staticmethod
    def create_low_stock_notification(product):
        """Notifica al vendedor cuando el stock está bajo."""
        if product.stock <= 5 and product.stock > 0:
            # Solo notificar si no hay una notificación reciente similar
            from django.utils import timezone
            from datetime import timedelta
            
            recent_notification = Notification.objects.filter(
                recipient=product.seller,
                notification_type=Notification.TYPE_LOW_STOCK,
                related_product_id=product.id,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if not recent_notification:
                Notification.objects.create(
                    recipient=product.seller,
                    notification_type=Notification.TYPE_LOW_STOCK,
                    title="Stock bajo en tu producto",
                    message=f"Quedan solo {product.stock} unidades de '{product.title}'",
                    link=f"/market/product/{product.id}/edit/",
                    related_product_id=product.id
                )
    
    @staticmethod
    def create_sold_out_notification(product):
        """Notifica al vendedor cuando un producto se agota."""
        Notification.objects.create(
            recipient=product.seller,
            notification_type=Notification.TYPE_PRODUCT_SOLD_OUT,
            title="Producto agotado",
            message=f"'{product.title}' se ha agotado. Actualiza el stock para seguir vendiendo.",
            link=f"/market/product/{product.id}/edit/",
            related_product_id=product.id
        )
