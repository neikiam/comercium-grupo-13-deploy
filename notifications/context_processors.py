from .models import Notification, Follow


def notifications(request):
    """Context processor para notificaciones y seguimiento."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        followers_count = Follow.objects.filter(following=request.user).count()
        following_count = Follow.objects.filter(follower=request.user).count()
        
        return {
            'unread_notifications_count': unread_count,
            'followers_count': followers_count,
            'following_count': following_count,
        }
    return {
        'unread_notifications_count': 0,
        'followers_count': 0,
        'following_count': 0,
    }
