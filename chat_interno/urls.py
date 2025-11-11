from django.urls import path

from . import views

app_name = "chat_interno"
urlpatterns = [
    path("", views.chat_home, name="home"),
    path("general/", views.chat_view, name="chat"),
    path("api/messages/", views.messages_api, name="messages-api"),
    path("api/post/", views.post_message_api, name="post-api"),
    path("api/search-users/", views.search_users_api, name="search-users"),
    path("private/", views.private_list, name="private-list"),
    path("private/start/<int:user_id>/", views.private_start, name="private-start"),
    path("private/start/by-username/", views.private_start_by_username, name="private-start-by-username"),
    path("private/<int:thread_id>/", views.private_chat, name="private-chat"),
    path("api/private/<int:thread_id>/messages/", views.private_messages_api, name="private-messages"),
    path("api/private/<int:thread_id>/post/", views.private_post_message_api, name="private-post"),
    # Requests
    path("requests/", views.requests_list, name="requests-list"),
    path("requests/send/<int:user_id>/", views.request_send, name="request-send"),
    path("requests/accept/<int:request_id>/", views.request_accept, name="request-accept"),
    path("requests/decline/<int:request_id>/", views.request_decline, name="request-decline"),
    path("requests/cancel/<int:request_id>/", views.request_cancel, name="request-cancel"),
    # Blocking
    path("blocked/", views.blocked_list, name="blocked-list"),
    path("blocked/block/<int:user_id>/", views.block_user, name="block-user"),
    path("blocked/unblock/<int:user_id>/", views.unblock_user, name="unblock-user"),
]
