from django.urls import path
from rest_framework.routers import SimpleRouter

from core.controllers import ChatRoomAPI, ChatMessageAPI, LoginAPI, SignupAPI, ChatActionsAPI, ProfileAPI

router = SimpleRouter()
router.register("chat-rooms", ChatRoomAPI)
router.register("chat-messages", ChatMessageAPI)

urlpatterns = [
	path("login/", LoginAPI.as_view()),
	path("signup/", SignupAPI.as_view()),
	path("chat-rooms/actions/", ChatActionsAPI.as_view()),
	path("profile/", ProfileAPI.as_view())
]
urlpatterns.extend(router.urls)