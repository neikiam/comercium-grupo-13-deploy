from django.urls import path

from . import views

app_name = 'perfil'

urlpatterns = [
    path('editar/', views.edit_profile, name='edit_profile'),
    path('ver_perfil/', views.profile_view, name='profile_view'),
    path('usuario/<int:user_id>/', views.user_profile_view, name='user_profile_view'),
    path('eliminar-avatar/', views.delete_avatar, name='delete_avatar'),
    # Moderación
    path('ban/<int:user_id>/confirm/', views.ban_user_confirm, name='ban_user_confirm'),
    path('ban/<int:user_id>/', views.ban_user, name='ban_user'),
]