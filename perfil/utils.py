"""
Utilidades para el módulo de perfil de usuario.
"""


def get_user_avatar_url(user, size=200):
    """
    Obtiene la URL del avatar de un usuario.
    
    Args:
        user: Instancia del modelo User
        size: Tamaño del avatar generado si no tiene imagen (default: 200)
    
    Returns:
        str: URL del avatar del usuario o avatar generado por defecto
    """
    if user and hasattr(user, 'profile') and user.profile and user.profile.avatar:
        return user.profile.avatar.url
    
    username = user.username if user else "Anon"
    return f"https://ui-avatars.com/api/?name={username}&background=random&size={size}"
