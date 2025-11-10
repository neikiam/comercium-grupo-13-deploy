from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    
    mp_access_token = models.CharField(max_length=255, blank=True, null=True, help_text="MercadoPago access token del vendedor")
    mp_refresh_token = models.CharField(max_length=255, blank=True, null=True, help_text="MercadoPago refresh token")
    mp_public_key = models.CharField(max_length=255, blank=True, null=True, help_text="MercadoPago public key del vendedor")
    mp_user_id = models.CharField(max_length=50, blank=True, null=True, help_text="ID de usuario en MercadoPago")
    mp_connected_at = models.DateTimeField(blank=True, null=True, help_text="Fecha de conexión con MercadoPago")
    
    def __str__(self):
        return self.user.username
    
    @property
    def has_mercadopago_connected(self):
        """Verifica si el usuario tiene MercadoPago conectado."""
        return bool(self.mp_access_token and self.mp_user_id)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
