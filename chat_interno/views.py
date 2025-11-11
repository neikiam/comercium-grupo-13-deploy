from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from perfil.utils import get_user_avatar_url

from .models import ChatMessage, DirectMessage, DirectMessageThread, BlockedUser, ChatRequest


def _is_blocked(user_a, user_b) -> bool:
    """Retorna True si existe bloqueo en cualquier dirección entre user_a y user_b."""
    return BlockedUser.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


@login_required
def chat_home(request):
    """Pantalla de inicio del chat con accesos a general, privados, solicitudes y bloqueados."""
    pending_incoming = ChatRequest.objects.filter(target=request.user, status=ChatRequest.STATUS_REQUESTED).count()
    pending_outgoing = ChatRequest.objects.filter(requester=request.user, status=ChatRequest.STATUS_REQUESTED).count()
    context = {
        "pending_incoming": pending_incoming,
        "pending_outgoing": pending_outgoing,
    }
    return render(request, "chat_home.html", context)


@login_required
def chat_view(request):
    return render(request, "chat.html")

@login_required
@ratelimit(key="user_or_ip", rate="60/m", method="GET", block=True)
def messages_api(request):
    """
    API para obtener mensajes del chat público con paginación.
    
    Args:
        request: HttpRequest con parámetros opcionales:
            - after_id: para polling incremental
            - limit: máximo de mensajes (default: 50)
    
    Returns:
        JsonResponse con lista de mensajes
    """
    after = request.GET.get("after_id")
    try:
        limit = min(int(request.GET.get("limit", 50)), 100)  # Max 100 mensajes
    except (ValueError, TypeError):
        limit = 50
    
    qs = ChatMessage.objects.select_related("user", "user__profile").all()
    if after:
        try:
            qs = qs.filter(id__gt=int(after))
        except (ValueError, TypeError):
            pass 
    
    qs = qs[:limit]
    
    msgs = []
    for m in qs:
        if m.user:
            avatar = get_user_avatar_url(m.user)
            username = m.user.username
            user_id = m.user.id
        else:
            avatar = None
            username = "Anon"
            user_id = None
        
        msgs.append({
            "id": m.id,
            "user_id": user_id,
            "user": username,
            "avatar": avatar,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
        })
    return JsonResponse({"messages": msgs})

@login_required
@require_POST
@ratelimit(key="user_or_ip", rate="10/m", method="POST", block=True)
def post_message_api(request):
    """
    API para publicar un mensaje en el chat público.
    
    Args:
        request: HttpRequest con POST data 'text'
    
    Returns:
        JsonResponse con id y timestamp del mensaje creado
    """
    user = request.user
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty"}, status=400)
    m = ChatMessage.objects.create(user=user, text=text)
    return JsonResponse({"id": m.id, "created_at": m.created_at.isoformat()})


@login_required
def private_list(request):
    """
    Vista para listar todas las conversaciones privadas del usuario.
    
    Args:
        request: HttpRequest
    
    Returns:
        HttpResponse con template de lista de conversaciones
    """
    user = request.user
    threads = DirectMessageThread.objects.filter(user1=user) | DirectMessageThread.objects.filter(user2=user)
    threads = threads.select_related("user1", "user2", "user1__profile", "user2__profile").order_by("-created_at")
    return render(request, "private_list.html", {"threads": threads})


@login_required
def private_chat(request, thread_id: int):
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    
    other = thread.user1 if thread.user2 == request.user else thread.user2
    
    # Detectar si hay bloqueo
    is_blocked = _is_blocked(thread.user1, thread.user2)
    blocked_by_other = False
    blocked_by_me = False
    
    if is_blocked:
        # Determinar quién bloqueó a quién
        blocked_by_other = BlockedUser.objects.filter(blocker=other, blocked=request.user).exists()
        blocked_by_me = BlockedUser.objects.filter(blocker=request.user, blocked=other).exists()
    
    # Verificar si hay una solicitud aceptada válida (incluso sin bloqueo)
    has_accepted_request = ChatRequest.objects.filter(
        (
            Q(requester=request.user, target=other) |
            Q(requester=other, target=request.user)
        ),
        status=ChatRequest.STATUS_ACCEPTED,
    ).exists()
    
    # Se puede escribir solo si NO hay bloqueo Y hay solicitud aceptada
    can_write = not is_blocked and has_accepted_request
    
    return render(request, "private_chat.html", {
        "thread": thread, 
        "other": other,
        "is_blocked": is_blocked,
        "blocked_by_other": blocked_by_other,
        "blocked_by_me": blocked_by_me,
        "can_write": can_write,
        "has_accepted_request": has_accepted_request
    })


@login_required
def private_start(request, user_id: int):
    User = get_user_model()
    other = get_object_or_404(User, id=user_id)
    if other == request.user:
        return redirect("chat_interno:private-list")
    
    # Bloqueo: si cualquiera bloqueó a la otra parte, no permitir
    if _is_blocked(request.user, other):
        messages.error(request, "No puedes iniciar un chat con este usuario debido a un bloqueo mutuo.")
        # Redirigir al perfil del usuario o a la página anterior
        referer = request.META.get('HTTP_REFERER')
        if referer and 'profiles' in referer:
            return redirect("perfil:user_profile_view", user_id=user_id)
        return redirect("chat_interno:private-list")
    
    # Verificar si existe una solicitud aceptada entre ambos
    has_accepted = ChatRequest.objects.filter(
        (
            Q(requester=request.user, target=other) |
            Q(requester=other, target=request.user)
        ),
        status=ChatRequest.STATUS_ACCEPTED,
    ).exists()
    
    # Si hay solicitud aceptada, crear o redirigir al hilo
    if has_accepted:
        a, b = (request.user, other) if request.user.id < other.id else (other, request.user)
        thread = DirectMessageThread.objects.filter(user1=a, user2=b).first()
        if thread:
            return redirect("chat_interno:private-chat", thread_id=thread.id)
        try:
            thread = DirectMessageThread.objects.create(user1=a, user2=b)
        except IntegrityError:
            thread = DirectMessageThread.objects.get(user1=a, user2=b)
        return redirect("chat_interno:private-chat", thread_id=thread.id)
    
    # Si no hay solicitud aceptada pero existe un hilo, significa que hubo un bloqueo/desbloqueo
    # Redirigir al hilo para que vean que no pueden escribir
    a, b = (request.user, other) if request.user.id < other.id else (other, request.user)
    thread = DirectMessageThread.objects.filter(user1=a, user2=b).first()
    if thread:
        messages.warning(request, "Necesitas una solicitud de chat aceptada para poder escribir mensajes.")
        return redirect("chat_interno:private-chat", thread_id=thread.id)
    
    # No hay hilo ni solicitud aceptada, enviar o reiterar solicitud
    ChatRequest.objects.get_or_create(requester=request.user, target=other, status=ChatRequest.STATUS_REQUESTED)
    messages.info(request, "Solicitud de chat enviada. Espera la aceptación del usuario.")
    return redirect("chat_interno:requests-list")


@login_required
def private_start_by_username(request):
    if request.method != "POST":
        return HttpResponseForbidden()
    username = request.POST.get("username", "").strip()
    if not username:
        return redirect("chat_interno:private-list")
    
    User = get_user_model()
    
    # Búsqueda flexible: busca coincidencias exactas primero, luego parciales
    try:
        # Intenta encontrar coincidencia exacta (case-insensitive)
        other = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        # Si no hay coincidencia exacta, busca coincidencias parciales
        matches = User.objects.filter(
            Q(username__icontains=username) | 
            Q(first_name__icontains=username) | 
            Q(last_name__icontains=username)
        ).exclude(id=request.user.id).only('id', 'username', 'first_name', 'last_name')[:10]
        
        if matches.count() == 0:
            # No se encontró ningún usuario
            threads = DirectMessageThread.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).select_related("user1", "user2").order_by("-created_at")
            
            return render(request, "private_list.html", {
                "threads": threads,
                "error_message": f'No se encontró ningún usuario con "{username}"',
                "search_query": username
            })
        elif matches.count() == 1:
            # Solo una coincidencia, usar esa
            other = matches.first()
        else:
            # Múltiples coincidencias, mostrar para que el usuario elija
            threads = DirectMessageThread.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).select_related("user1", "user2").order_by("-created_at")
            
            return render(request, "private_list.html", {
                "threads": threads,
                "user_suggestions": matches,
                "search_query": username
            })
    except User.MultipleObjectsReturned:
        # No debería pasar con username único, pero por si acaso
        other = User.objects.filter(username__iexact=username).first()
    
    if other == request.user:
        return redirect("chat_interno:private-list")
    
    # Redirigir al perfil del usuario en lugar de enviar solicitud automática
    return redirect("perfil:user_profile_view", user_id=other.id)


@login_required
@ratelimit(key="user_or_ip", rate="30/m", method="GET", block=True)
def search_users_api(request):
    """
    API para buscar usuarios en tiempo real (autocompletado).
    
    Args:
        request: HttpRequest con parámetro 'q' (query de búsqueda)
    
    Returns:
        JsonResponse con lista de usuarios coincidentes
    """
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"users": []})
    
    User = get_user_model()
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related("profile").only(
        'id', 'username', 'first_name', 'last_name', 'profile__avatar'
    )[:10]
    
    results = []
    for u in users:
        avatar = get_user_avatar_url(u, size=40)
        display_name = u.get_full_name() or u.username
        results.append({
            "id": u.id,
            "username": u.username,
            "display_name": display_name,
            "avatar": avatar
        })
    
    return JsonResponse({"users": results})


@login_required
@ratelimit(key="user_or_ip", rate="60/m", method="GET", block=True)
def private_messages_api(request, thread_id: int):
    """
    API para obtener mensajes de una conversación privada con paginación.
    
    Args:
        request: HttpRequest con parámetros opcionales:
            - after_id: para polling incremental
            - limit: máximo de mensajes (default: 50)
        thread_id: ID del hilo de conversación
    
    Returns:
        JsonResponse con lista de mensajes privados
    """
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    if _is_blocked(thread.user1, thread.user2):
        return HttpResponseForbidden()
    
    after = request.GET.get("after_id")
    try:
        limit = min(int(request.GET.get("limit", 50)), 100)  # Max 100 mensajes
    except (ValueError, TypeError):
        limit = 50
    
    qs = thread.messages.select_related("user", "user__profile").all()
    if after:
        try:
            qs = qs.filter(id__gt=int(after))
        except (ValueError, TypeError):
            pass
    
    qs = qs[:limit]
    
    msgs = []
    for m in qs:
        if m.user:
            avatar = get_user_avatar_url(m.user)
            username = m.user.username
            user_id = m.user.id
        else:
            avatar = None
            username = "Anon"
            user_id = None
        
        msgs.append({
            "id": m.id,
            "user_id": user_id,
            "user": username,
            "avatar": avatar,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
        })
    return JsonResponse({"messages": msgs})


@login_required
@require_POST
@ratelimit(key="user_or_ip", rate="10/m", method="POST", block=True)
def private_post_message_api(request, thread_id: int):
    """
    API para publicar un mensaje en una conversación privada.
    
    Args:
        request: HttpRequest con POST data 'text'
        thread_id: ID del hilo de conversación
    
    Returns:
        JsonResponse con id y timestamp del mensaje creado
    """
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    if _is_blocked(thread.user1, thread.user2):
        return JsonResponse({"error": "blocked", "message": "No puedes enviar mensajes debido a un bloqueo."}, status=403)
    
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty"}, status=400)
    
    m = DirectMessage.objects.create(thread=thread, user=request.user, text=text)
    return JsonResponse({"id": m.id, "created_at": m.created_at.isoformat()})


# -------------------- Chat Requests --------------------

@login_required
def requests_list(request):
    incoming = ChatRequest.objects.filter(target=request.user, status=ChatRequest.STATUS_REQUESTED).select_related("requester", "requester__profile").order_by("-created_at")
    outgoing = ChatRequest.objects.filter(requester=request.user, status=ChatRequest.STATUS_REQUESTED).select_related("target", "target__profile").order_by("-created_at")
    context = {
        "incoming": incoming,
        "outgoing": outgoing,
    }
    return render(request, "requests_list.html", context)


@login_required
@require_POST
def request_send(request, user_id: int):
    User = get_user_model()
    other = get_object_or_404(User, id=user_id)
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if other == request.user:
        if is_ajax:
            return JsonResponse({"error": "No puedes enviarte una solicitud a ti mismo."}, status=400)
        messages.warning(request, "No puedes enviarte una solicitud de chat a ti mismo.")
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect("chat_interno:requests-list")
    
    if _is_blocked(request.user, other):
        if is_ajax:
            return JsonResponse({"error": "No puedes enviar una solicitud debido a un bloqueo mutuo."}, status=403)
        messages.error(request, "No puedes enviar una solicitud de chat debido a un bloqueo mutuo.")
        # Redirigir a la página anterior (probablemente el perfil)
        referer = request.META.get('HTTP_REFERER')
        if referer and 'profiles' in referer:
            return redirect("perfil:user_profile_view", user_id=user_id)
        return redirect("chat_interno:requests-list")
    
    chat_request, created = ChatRequest.objects.get_or_create(requester=request.user, target=other, status=ChatRequest.STATUS_REQUESTED)
    
    if created:
        from notifications.services import NotificationService
        NotificationService.create_chat_request_notification(request.user, other)
    
    if is_ajax:
        return JsonResponse({"success": True, "message": f"Solicitud enviada a {other.username}"})
    
    messages.success(request, f"Solicitud de chat enviada a {other.username}.")
    
    # Redirigir a la página anterior
    referer = request.META.get('HTTP_REFERER')
    if referer and 'profiles' in referer:
        return redirect("perfil:user_profile_view", user_id=user_id)
    return redirect("chat_interno:requests-list")


@login_required
@require_POST
def request_accept(request, request_id: int):
    cr = get_object_or_404(ChatRequest, id=request_id, target=request.user)
    if _is_blocked(request.user, cr.requester):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"error": "No puedes aceptar: existe un bloqueo."}, status=400)
        messages.error(request, "No puedes aceptar: existe un bloqueo.")
        return redirect("chat_interno:requests-list")
    
    cr.accept()
    
    from notifications.services import NotificationService
    NotificationService.create_chat_accepted_notification(cr.requester, cr.target)
    
    # Crear hilo si no existe
    a, b = (cr.requester, cr.target) if cr.requester.id < cr.target.id else (cr.target, cr.requester)
    thread, _ = DirectMessageThread.objects.get_or_create(user1=a, user2=b)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": True, "thread_id": thread.id})
    
    messages.success(request, "Solicitud aceptada. Conversación creada.")
    return redirect("chat_interno:private-chat", thread_id=thread.id)


@login_required
@require_POST
def request_decline(request, request_id: int):
    cr = get_object_or_404(ChatRequest, id=request_id, target=request.user)
    cr.decline()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": True})
    
    messages.info(request, "Solicitud rechazada.")
    return redirect("chat_interno:requests-list")


@login_required
@require_POST
def request_cancel(request, request_id: int):
    """Permite al remitente cancelar una solicitud pendiente."""
    cr = get_object_or_404(ChatRequest, id=request_id, requester=request.user, status=ChatRequest.STATUS_REQUESTED)
    cr.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": True})
    
    messages.info(request, "Solicitud cancelada.")
    return redirect("chat_interno:requests-list")


# -------------------- Blocking --------------------

@login_required
def blocked_list(request):
    blocks = BlockedUser.objects.filter(blocker=request.user).select_related("blocked", "blocked__profile").order_by("-created_at")
    return render(request, "blocked_list.html", {"blocks": blocks})


@login_required
@require_POST
def block_user(request, user_id: int):
    User = get_user_model()
    other = get_object_or_404(User, id=user_id)
    if other == request.user:
        return redirect("chat_interno:blocked-list")
    BlockedUser.objects.get_or_create(blocker=request.user, blocked=other)
    
    # Invalidar TODAS las solicitudes entre ambos (pendientes Y aceptadas)
    ChatRequest.objects.filter(
        Q(requester=request.user, target=other) | Q(requester=other, target=request.user)
    ).update(status=ChatRequest.STATUS_DECLINED)
    
    messages.success(request, f"Usuario {other.username} bloqueado.")
    return redirect("chat_interno:blocked-list")


@login_required
@require_POST
def unblock_user(request, user_id: int):
    User = get_user_model()
    other = get_object_or_404(User, id=user_id)
    BlockedUser.objects.filter(blocker=request.user, blocked=other).delete()
    
    # Invalidar solicitudes de chat aceptadas entre ambos
    # Para que tengan que volver a enviar solicitud
    ChatRequest.objects.filter(
        Q(requester=request.user, target=other) | Q(requester=other, target=request.user),
        status=ChatRequest.STATUS_ACCEPTED,
    ).update(status=ChatRequest.STATUS_DECLINED)
    
    messages.success(request, f"Usuario {other.username} desbloqueado. Deberán enviarse solicitudes de chat nuevamente.")
    return redirect("chat_interno:blocked-list")
