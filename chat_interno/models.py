from django.conf import settings
from django.db import models
from django.utils import timezone


class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class DirectMessageThread(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dm_threads_as_user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dm_threads_as_user2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_dm_thread_pair")
        ]

    def participants(self):
        return (self.user1, self.user2)


class DirectMessage(models.Model):
    thread = models.ForeignKey(DirectMessageThread, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class BlockedUser(models.Model):
    """Relación de bloqueo entre usuarios.

    Un registro significa que 'blocker' bloquea a 'blocked'. Se utiliza para
    impedir creación de hilos y envío/lectura de mensajes privados.
    """
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_made",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block_pair")
        ]
        indexes = [
            models.Index(fields=["blocker"]),
            models.Index(fields=["blocked"]),
        ]

    def __str__(self):
        return f"{self.blocker_id} bloqueó {self.blocked_id}"


class ChatRequest(models.Model):
    """Solicitud para iniciar un chat privado.

    Flujo:
    - requester envía solicitud a target (status=requested)
    - target acepta => status=accepted y se crea/obtiene el hilo
    - target rechaza => status=declined

    No se pueden duplicar solicitudes pendientes entre el mismo par.
    """
    STATUS_REQUESTED = "requested"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Solicitada"),
        (STATUS_ACCEPTED, "Aceptada"),
        (STATUS_DECLINED, "Rechazada"),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_requests_sent",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_requests_received",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "target"],
                condition=models.Q(status="requested"),
                name="unique_pending_chat_request",
            )
        ]
        indexes = [
            models.Index(fields=["requester"]),
            models.Index(fields=["target"]),
            models.Index(fields=["status"]),
        ]

    def accept(self):
        if self.status != self.STATUS_REQUESTED:
            return
        self.status = self.STATUS_ACCEPTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def decline(self):
        if self.status != self.STATUS_REQUESTED:
            return
        self.status = self.STATUS_DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def __str__(self):
        return f"ChatRequest {self.requester_id}->{self.target_id} ({self.status})"
