from django import template
from django.contrib.auth import get_user_model

register = template.Library()

User = get_user_model()


@register.simple_tag
def user_avatar(user, size=100):
    """
    Retorna la URL del avatar del usuario.
    Si no tiene avatar, usa UI Avatars.
    
    Uso: {% user_avatar user 32 %}
    """
    if hasattr(user, 'profile') and user.profile.avatar:
        return user.profile.avatar.url
    
    # Generar avatar con iniciales usando UI Avatars
    username = user.username if user else "U"
    return f"https://ui-avatars.com/api/?name={username}&size={size}&background=random"
