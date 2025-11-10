"""
Señales para el módulo mercado.
Manejo de eventos del ciclo de vida de modelos.
"""
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import CartItem, Product


@receiver(post_save, sender=Product)
def notify_followers_on_new_product(sender, instance, created, **kwargs):
    """
    Notifica a los seguidores cuando se crea un nuevo producto.
    
    Args:
        sender: Modelo Product
        instance: Instancia de Product
        created: True si es un nuevo producto
        **kwargs: Argumentos adicionales de la señal
    """
    if created and instance.active:
        from notifications.services import NotificationService
        NotificationService.create_new_product_notification(instance)


@receiver(pre_delete, sender=Product)
def cleanup_cartitems_on_product_delete(sender, instance, **kwargs):
    """
    Elimina items del carrito cuando un producto es eliminado.
    
    Args:
        sender: Modelo Product
        instance: Instancia de Product siendo eliminada
        **kwargs: Argumentos adicionales de la señal
    """
    CartItem.objects.filter(product=instance).delete()


@receiver(post_delete, sender=Product)
def cleanup_product_image_on_delete(sender, instance, **kwargs):
    """
    Elimina archivo de imagen del almacenamiento cuando se elimina un Product.
    
    Args:
        sender: Modelo Product
        instance: Instancia de Product eliminada
        **kwargs: Argumentos adicionales de la señal
    """
    try:
        if instance.image:
            instance.image.delete(save=False)
    except Exception:
        pass
