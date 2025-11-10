from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # Notificaciones
    path("", views.notification_list, name="list"),
    path("<int:notification_id>/read/", views.mark_notification_read, name="mark-read"),
    path("mark-all-read/", views.mark_all_read, name="mark-all-read"),
    path("count/", views.notification_count, name="count"),
    
    # Seguimiento
    path("follow/<int:user_id>/", views.follow_user, name="follow"),
    path("unfollow/<int:user_id>/", views.unfollow_user, name="unfollow"),
    path("followers/<str:username>/", views.followers_list, name="followers"),
    path("following/<str:username>/", views.following_list, name="following"),
    path("feed/", views.following_feed, name="feed"),
]
