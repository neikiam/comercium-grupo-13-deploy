import logging
import requests
from datetime import datetime
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.conf import settings

from mercado.models import Product

from .forms import ProfileForm

logger = logging.getLogger(__name__)
User = get_user_model()


def is_staff_or_superuser(user):
    """Helper para verificar si el usuario es staff o superusuario."""
    return user.is_staff or user.is_superuser

@login_required
def profile_view(request):
    """
    Muestra el perfil del usuario autenticado y sus productos activos.
    
    Args:
        request: HttpRequest
    
    Returns:
        HttpResponse con template de perfil
    """
    profile = request.user.profile
    # Mostrar solo productos activos del usuario para evitar ver eliminados o pausados
    user_products = Product.objects.filter(seller=request.user, active=True).select_related('seller').order_by('-created_at')
    
    context = {
        "profile": profile,
        "user_products": user_products,
        "is_own_profile": True,
    }
    return render(request, "profile.html", context)


@login_required
def user_profile_view(request, user_id):
    """
    Muestra el perfil de cualquier usuario y sus productos activos.
    
    Args:
        request: HttpRequest
        user_id: ID del usuario a visualizar
    
    Returns:
        HttpResponse con template de perfil
    """
    from notifications.models import Follow
    
    viewed_user = get_object_or_404(User, id=user_id)
    profile = viewed_user.profile
    user_products = Product.objects.filter(seller=viewed_user, active=True).select_related('seller').order_by('-created_at')
    
    # Verificar si el usuario autenticado sigue al usuario visto
    is_following = False
    if request.user.is_authenticated and request.user != viewed_user:
        is_following = Follow.objects.filter(follower=request.user, following=viewed_user).exists()
    
    # Contar seguidores y seguidos
    followers_count = Follow.objects.filter(following=viewed_user).count()
    following_count = Follow.objects.filter(follower=viewed_user).count()
    
    context = {
        "profile": profile,
        "user_products": user_products,
        "viewed_user": viewed_user,
        "is_own_profile": request.user == viewed_user,
        "is_following": is_following,
        "followers_count": followers_count,
        "following_count": following_count,
    }
    return render(request, "profile.html", context)


@login_required
def edit_profile(request):
    """
    Permite editar el perfil del usuario autenticado.
    
    Args:
        request: HttpRequest (POST con form data o GET para mostrar formulario)
    
    Returns:
        HttpResponse con formulario o redirect a perfil
    """
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            logger.info(f"Perfil actualizado para usuario {request.user.id}")
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect("perfil:profile_view")
        else:
            messages.error(request, "Hubo un error al actualizar tu perfil. Revisa los datos.")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "profile_edit.html", {"form": form})


@login_required
def delete_avatar(request):
    """
    Elimina el avatar del usuario autenticado.
    
    Args:
        request: HttpRequest (POST para confirmar)
    
    Returns:
        Redirect a edición de perfil
    """
    if request.method == "POST":
        profile = request.user.profile
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save()
            logger.info(f"Avatar eliminado para usuario {request.user.id}")
            messages.success(request, "Tu foto de perfil ha sido eliminada.")
        else:
            messages.info(request, "No tienes una foto de perfil para eliminar.")
        return redirect("perfil:edit_profile")
    return redirect("perfil:edit_profile")


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def ban_user_confirm(request, user_id):
    """Vista de confirmación antes de banear."""
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user == request.user:
        messages.error(request, "No puedes banearte a ti mismo.")
        return redirect('perfil:user_profile_view', user_id=user_id)
    
    # staff no puede banear a superuser, solo superuser puede banear a staff
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "No tienes permiso para banear a un superusuario.")
        return redirect('perfil:user_profile_view', user_id=user_id)
    
    if target_user.is_staff and not request.user.is_superuser:
        messages.error(request, "Solo un superusuario puede banear a staff.")
        return redirect('perfil:user_profile_view', user_id=user_id)
    
    return render(request, 'ban_user_confirm.html', {'target_user': target_user})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def ban_user(request, user_id):
    """Endpoint para confirmar y ejecutar el baneo."""
    if request.method != 'POST':
        return redirect('perfil:ban_user_confirm', user_id=user_id)
    
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user == request.user:
        messages.error(request, "No puedes banearte a ti mismo.")
        return redirect('perfil:ban_user_confirm', user_id=user_id)
    
    # staff no puede banear a superuser, solo superuser puede banear a staff
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "No tienes permiso para banear a un superusuario.")
        return redirect('perfil:user_profile_view', user_id=user_id)
    
    if target_user.is_staff and not request.user.is_superuser:
        messages.error(request, "Solo un superusuario puede banear a staff.")
        return redirect('perfil:user_profile_view', user_id=user_id)
    
    # Ejecutar baneo
    username = target_user.username
    target_user.delete()  # CASCADE eliminará Profile y Products
    messages.success(request, f"Usuario {username} ha sido baneado y eliminado del sistema.")
    return redirect('core:index')


# ============================================
# MercadoPago Marketplace OAuth
# ============================================

@login_required
def mercadopago_settings(request):
    """
    Página de configuración de MercadoPago del usuario.
    """
    profile = request.user.profile
    platform_fee = settings.MERCADOPAGO_PLATFORM_FEE_PERCENTAGE
    seller_percentage = 100 - platform_fee
    mp_app_configured = bool(settings.MERCADOPAGO_APP_ID and settings.MERCADOPAGO_CLIENT_SECRET)
    
    context = {
        'profile': profile,
        'platform_fee': platform_fee,
        'seller_percentage': seller_percentage,
        'mp_app_configured': mp_app_configured,
    }
    return render(request, 'mercadopago_settings.html', context)


@login_required
def mercadopago_connect(request):
    """
    Inicia el flujo OAuth de MercadoPago para conectar la cuenta del vendedor.
    """
    app_id = settings.MERCADOPAGO_APP_ID
    redirect_uri = settings.MERCADOPAGO_REDIRECT_URI
    
    if not app_id:
        messages.error(request, "MercadoPago Marketplace no está configurado. Contacta al administrador.")
        return redirect('perfil:profile_view')
    
    auth_url = (
        f"https://auth.mercadopago.com.ar/authorization"
        f"?client_id={app_id}"
        f"&response_type=code"
        f"&platform_id=mp"
        f"&redirect_uri={redirect_uri}"
    )
    
    logger.info(f"Usuario {request.user.id} iniciando OAuth con MercadoPago")
    return redirect(auth_url)


@login_required
def mercadopago_callback(request):
    """
    Callback de OAuth de MercadoPago. Recibe el código de autorización y lo intercambia por tokens.
    """
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        logger.error(f"Error en OAuth de MercadoPago para usuario {request.user.id}: {error}")
        messages.error(request, f"Error al conectar con MercadoPago: {error}")
        return redirect('perfil:profile_view')
    
    if not code:
        messages.error(request, "No se recibió el código de autorización de MercadoPago.")
        return redirect('perfil:profile_view')
    
    app_id = settings.MERCADOPAGO_APP_ID
    client_secret = settings.MERCADOPAGO_CLIENT_SECRET
    redirect_uri = settings.MERCADOPAGO_REDIRECT_URI
    
    token_url = "https://api.mercadopago.com/oauth/token"
    payload = {
        "client_id": app_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    
    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        profile = request.user.profile
        profile.mp_access_token = data.get('access_token')
        profile.mp_refresh_token = data.get('refresh_token')
        profile.mp_public_key = data.get('public_key')
        profile.mp_user_id = data.get('user_id')
        profile.mp_connected_at = timezone.now()
        profile.save()
        
        logger.info(f"Usuario {request.user.id} conectó exitosamente su cuenta de MercadoPago (ID: {profile.mp_user_id})")
        messages.success(request, "¡Tu cuenta de MercadoPago ha sido conectada exitosamente! Ahora puedes recibir pagos directamente.")
        
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error al intercambiar código OAuth para usuario {request.user.id}: {e}")
        messages.error(request, "Hubo un error al conectar con MercadoPago. Intenta nuevamente.")
    
    return redirect('perfil:profile_view')


@login_required
@require_POST
def mercadopago_disconnect(request):
    """
    Desconecta la cuenta de MercadoPago del usuario.
    """
    profile = request.user.profile
    profile.mp_access_token = None
    profile.mp_refresh_token = None
    profile.mp_public_key = None
    profile.mp_user_id = None
    profile.mp_connected_at = None
    profile.save()
    
    logger.info(f"Usuario {request.user.id} desconectó su cuenta de MercadoPago")
    messages.success(request, "Tu cuenta de MercadoPago ha sido desconectada.")
    
    return redirect('perfil:profile_view')
