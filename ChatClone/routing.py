from django.urls import path

from core.consumers import ChatConsumer, GeneralConsumer, PrivateConsumer

websocket_urlpatterns = [
    path("ws/<token>/chats/<chat_id>/", ChatConsumer.as_asgi()),
    path("ws/<token>/general/", GeneralConsumer.as_asgi()),
    path("ws/<token>/private/", PrivateConsumer.as_asgi())
]
