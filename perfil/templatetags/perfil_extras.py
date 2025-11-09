from django import template
from perfil.utils import get_user_avatar_url

register = template.Library()

@register.simple_tag
def user_avatar(user, size=32):
    """Devuelve una URL segura para el avatar del usuario.
    Si falla o no tiene perfil/imagen, genera avatar por defecto.
    """
    try:
        return get_user_avatar_url(user, size=size)
    except Exception:
        username = getattr(user, 'username', 'Anon')
        return f"https://ui-avatars.com/api/?name={username}&background=random&size={size}"