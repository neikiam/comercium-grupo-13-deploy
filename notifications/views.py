from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import Notification, Follow
from .services import NotificationService

User = get_user_model()


@login_required
def notification_list(request):
    """Vista para listar todas las notificaciones del usuario."""
    notifications = Notification.objects.filter(recipient=request.user).select_related('related_user')[:50]
    
    # Marcar notificaciones como leídas al verlas
    unread_ids = [n.id for n in notifications if not n.is_read]
    if unread_ids:
        Notification.objects.filter(id__in=unread_ids).update(is_read=True)
    
    return render(request, "notifications/notification_list.html", {"notifications": notifications})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Marca una notificación como leída."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    return JsonResponse({"success": True})


@login_required
@require_POST
def mark_all_read(request):
    """Marca todas las notificaciones del usuario como leídas."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"success": True, "count": count})


@login_required
def notification_count(request):
    """API para obtener el contador de notificaciones no leídas."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"count": count})


@login_required
@require_POST
def follow_user(request, user_id):
    """Seguir a un usuario."""
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user == request.user:
        messages.error(request, "No puedes seguirte a ti mismo.")
        return redirect('perfil:user_profile_view', user_id=target_user.id)
    
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )
    
    if created:
        NotificationService.create_follower_notification(request.user, target_user)
        messages.success(request, f"Ahora sigues a {target_user.username}")
    else:
        messages.info(request, f"Ya sigues a {target_user.username}")
    
    return redirect('perfil:user_profile_view', user_id=target_user.id)


@login_required
@require_POST
def unfollow_user(request, user_id):
    """Dejar de seguir a un usuario."""
    target_user = get_object_or_404(User, id=user_id)
    
    deleted_count = Follow.objects.filter(
        follower=request.user,
        following=target_user
    ).delete()[0]
    
    if deleted_count > 0:
        messages.success(request, f"Has dejado de seguir a {target_user.username}")
    else:
        messages.info(request, f"No seguías a {target_user.username}")
    
    return redirect('perfil:user_profile_view', user_id=target_user.id)


@login_required
def followers_list(request, username):
    """Lista de seguidores de un usuario."""
    user = get_object_or_404(User, username=username)
    followers = Follow.objects.filter(following=user).select_related('follower')
    
    return render(request, "notifications/followers_list.html", {
        "profile_user": user,
        "followers": followers
    })


@login_required
def following_list(request, username):
    """Lista de usuarios que sigue un usuario."""
    user = get_object_or_404(User, username=username)
    following = Follow.objects.filter(follower=user).select_related('following')
    
    return render(request, "notifications/following_list.html", {
        "profile_user": user,
        "following": following
    })


@login_required
def following_feed(request):
    """Feed de productos de usuarios que sigues."""
    from mercado.models import Product
    
    # Obtener IDs de usuarios que sigo
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    
    # Productos de esos usuarios
    products = Product.objects.filter(
        seller_id__in=following_ids,
        active=True
    ).select_related('seller').order_by('-created_at')[:50]
    
    return render(request, "notifications/following_feed.html", {"products": products})
