import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
    viewed_user = get_object_or_404(User, id=user_id)
    profile = viewed_user.profile
    user_products = Product.objects.filter(seller=viewed_user, active=True).select_related('seller').order_by('-created_at')
    
    context = {
        "profile": profile,
        "user_products": user_products,
        "viewed_user": viewed_user,
        "is_own_profile": request.user == viewed_user,
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
