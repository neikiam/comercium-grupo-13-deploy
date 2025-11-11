from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Sistema de notificaciones para usuarios."""
    
    # Tipos de notificaciones
    TYPE_NEW_SALE = "new_sale"
    TYPE_NEW_FOLLOWER = "new_follower"
    TYPE_NEW_PRODUCT = "new_product"  # Nuevo producto de alguien que sigues
    TYPE_PRODUCT_SOLD_OUT = "product_sold_out"  # Tu producto se agotó
    TYPE_LOW_STOCK = "low_stock"  # Stock bajo en tu producto
    TYPE_CHAT_REQUEST = "chat_request"  # Alguien te envió solicitud de chat
    TYPE_CHAT_ACCEPTED = "chat_accepted"  # Aceptaron tu solicitud de chat
    
    TYPE_CHOICES = [
        (TYPE_NEW_SALE, "Nueva venta"),
        (TYPE_NEW_FOLLOWER, "Nuevo seguidor"),
        (TYPE_NEW_PRODUCT, "Nuevo producto"),
        (TYPE_PRODUCT_SOLD_OUT, "Producto agotado"),
        (TYPE_LOW_STOCK, "Stock bajo"),
        (TYPE_CHAT_REQUEST, "Solicitud de chat"),
        (TYPE_CHAT_ACCEPTED, "Chat aceptado"),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Referencias opcionales (para construir el link y mensaje)
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications_triggered"
    )
    related_product_id = models.IntegerField(null=True, blank=True)
    related_order_id = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]


class Follow(models.Model):
    """Sistema de seguimiento entre usuarios."""
    
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F('following')),
                name='cannot_follow_self'
            ),
        ]
        indexes = [
            models.Index(fields=['follower', '-created_at']),
            models.Index(fields=['following', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.follower.username} sigue a {self.following.username}"
