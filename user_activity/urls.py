from django.urls import path

from . import views

app_name = "user_activity"
urlpatterns = [
    path("session-expired/", views.session_expired, name="session_expired"),
    path("online/", views.online_users, name="online-users"),
]