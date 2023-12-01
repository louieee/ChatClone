from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.helpers import send_ws_to_private
from core.models import ChatRoom, ChatMessage
from core.services import ChatMessageSerializer, CreateMessageSerializer, CreateChatRoomSerializer, \
	ChatRoomSerializer, ChatActionSerializer, LoginSerializer, SignupSerializer, UserSerializer, \
	ChatMessageListSerializer


# Create your views here.

class LoginAPI(APIView):
	permission_classes = (AllowAny,)
	http_method_names = ("post",)

	@swagger_auto_schema(
		request_body=LoginSerializer,
		operation_summary="logs a user in",
		tags=[
			"Auth",
		],
	)
	@transaction.atomic
	def post(self, request, *args, **kwargs):
		serializer = LoginSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors[0])
		token = serializer.save()
		return Response(token)


class SignupAPI(APIView):
	permission_classes = (AllowAny,)
	http_method_names = ("post",)

	@swagger_auto_schema(
		request_body=SignupSerializer,
		operation_summary="creates a new account",
		tags=[
			"Auth",
		],
	)
	@transaction.atomic
	def post(self, request, *args, **kwargs):
		serializer = SignupSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors)
		user = serializer.save()
		return Response(UserSerializer(user).data)


class ProfileAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ("get",)

	@swagger_auto_schema(
		operation_summary="enables user to view profile",
		tags=[
			"User",
		],
	)
	def get(self, request, *args, **kwargs):
		return Response(UserSerializer(request.user).data)


# endpoint to login

# endpoint to signup

class ChatRoomAPI(ModelViewSet):
	permission_classes = (IsAuthenticated,)
	queryset = ChatRoom.objects.all()
	http_method_names = ("get", "put", "post")
	serializer_class = ChatRoomSerializer

	def get_queryset(self):
		return self.queryset.filter(members__username=self.request.user.username)

	def get_serializer_context(self):
		data = super(ChatRoomAPI, self).get_serializer_context()
		data['user'] = self.request.user
		return data

	@swagger_auto_schema(
		request_body=CreateChatRoomSerializer,
		operation_summary="enables an admin update a chatroom",
		tags=[
			"ChatRoom",
		],
	)
	@transaction.atomic
	def update(self, request, *args, **kwargs):
		self.serializer_class = CreateChatRoomSerializer
		return super(ChatRoomAPI, self).update(request, *args, **kwargs)

	@swagger_auto_schema(
		request_body=CreateChatRoomSerializer,
		operation_summary="enables a user create a chatroom",
		tags=[
			"ChatRoom",
		],
	)
	@transaction.atomic
	def create(self, request, *args, **kwargs):
		self.serializer_class = CreateChatRoomSerializer
		return super(ChatRoomAPI, self).create(request, *args, **kwargs)

	@swagger_auto_schema(
		operation_summary="enables a user view list of chatrooms",
		tags=[
			"ChatRoom",
		],
	)
	def list(self, request, *args, **kwargs):
		return super(ChatRoomAPI, self).list(request, *args, **kwargs)

	@swagger_auto_schema(
		operation_summary="enables a user view  a chatroom",
		tags=[
			"ChatRoom",
		],
	)
	def retrieve(self, request, *args, **kwargs):
		return super(ChatRoomAPI, self).retrieve(request, *args, **kwargs)


class ChatMessageAPI(ModelViewSet):
	permission_classes = (IsAuthenticated,)
	queryset = ChatMessage.objects.all()
	http_method_names = ("get", "post")
	serializer_class = ChatMessageListSerializer
	parser_classes = (MultiPartParser,)

	chat_id = openapi.Parameter("chat_id", in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER)

	def get_serializer_context(self):
		data = super(ChatMessageAPI, self).get_serializer_context()
		data['user'] = self.request.user
		return data

	def get_queryset(self):
		if self.request.user.is_anonymous:
			return self.queryset.none()
		chat_id = self.request.query_params.get("chat_id")
		if not chat_id:
			return self.queryset.none()
		if not ChatRoom.objects.filter(id=chat_id, members__username=self.request.user.username).exists():
			return self.queryset.none()
		return self.queryset.filter(chat_id=chat_id)

	@swagger_auto_schema(
		request_body=CreateMessageSerializer,
		operation_summary="enables a user to send a chat message",
		tags=[
			"ChatRoom",
		],
	)
	@transaction.atomic
	def create(self, request, *args, **kwargs):
		serializer = CreateMessageSerializer(data=request.data, context={"user": request.user,
		                                                                 "files": request.FILES})
		serializer.is_valid(raise_exception=True)
		message = serializer.save()
		return Response(ChatMessageSerializer(message, context={"user": request.user}).data)

	@swagger_auto_schema(
		manual_parameters=[chat_id, ],
		operation_summary="enables a user view chat messages",
		tags=[
			"ChatRoom",
		],
	)
	def list(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())

		page = self.paginate_queryset(queryset)
		ids = (data.id for data in page)
		messages = queryset.filter(id__in=ids).exclude(viewers__username=self.request.user.username).\
		                                       exclude(sender=self.request.user)
		for message in messages:
			message.view(user=request.user)
			send_ws_to_private(user=message.sender, event="NEW MESSAGE VIEWER",
			                   data=ChatMessageListSerializer(message).data)
		serializer = self.get_serializer(page, many=True)
		return self.get_paginated_response(serializer.data)

	@swagger_auto_schema(
		manual_parameters=[chat_id],
		operation_summary="enables a user to view full details of a chat message",
		tags=[
			"ChatRoom",
		],
		responses={200: ChatMessageSerializer()}
	)
	def retrieve(self, request, *args, **kwargs):
		self.serializer_class = ChatMessageSerializer
		return super(ChatMessageAPI, self).retrieve(request, *args, **kwargs)


class ChatActionsAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ("post",)

	@swagger_auto_schema(
		request_body=ChatActionSerializer,
		operation_summary="enables a user join or leave a chatroom",
		tags=[
			"ChatRoom",
		],
	)
	@transaction.atomic
	def post(self, request, *args, **kwargs):
		serializer = ChatActionSerializer(data=request.data, context={"user": request.user})
		if not serializer.is_valid():
			return Response(serializer.errors)
		chatroom = serializer.save()
		return Response(ChatRoomSerializer(chatroom).data)
