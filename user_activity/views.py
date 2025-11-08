from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from .models import UserActivity


def online_users(request):
    cutoff = timezone.now() - timedelta(minutes=5)
    active = UserActivity.objects.filter(last_seen__gte=cutoff).select_related("user")
    return render(request, "online_users.html", {"active": active})


def session_expired(request):
    return render(request, "session_expired.html")
