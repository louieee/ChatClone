import json
import logging
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ChatClone.settings")
django.setup()
from asgiref.sync import async_to_sync  # noqa
from channels.generic.websocket import WebsocketConsumer  # noqa
from rest_framework.authtoken.models import Token  # noqa

from core.models import User, ChatRoom  # noqa


class ChatConsumer(WebsocketConsumer):
	"""
	This namespace handles all connections to individual chat rooms
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.user = None
		self.chat = None

	@staticmethod
	def is_authenticated(scope) -> User or None:
		token = scope["url_route"]["kwargs"]["token"]
		chat_id = scope['url_route']["kwargs"]["chat_id"]
		token_obj = Token.objects.filter(key__exact=token).first()
		if not token_obj:
			return None
		user = token_obj.user
		chat = ChatRoom.objects.filter(id=chat_id).first()
		if not chat.members.filter(id=user.id).exists():
			return None
		return chat, user

	def connect(self):
		self.chat, self.user = self.is_authenticated(self.scope)
		if not self.user:
			logging.critical("Authentication Refused")
			self.close()
			return
		async_to_sync(self.channel_layer.group_add)(str(self.chat), self.channel_name)
		self.accept()
		self.send(f"{self.user.username} just connected to {self.chat.name}")

	def websocket_receive(self, data):
		data = json.loads(data["text"])
		async_to_sync(self.channel_layer.group_send)(
			str(self.chat), {"type": "notify", "data": json.dumps(data)}
		)

	def notify(self, event):
		self.send(text_data=event["data"])

	def disconnect(self, code):
		super().disconnect(code)


class GeneralConsumer(WebsocketConsumer):
	"""
	This name space handles all connections to the general channel which everyone has access to
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.user = None

	@staticmethod
	def is_authenticated(scope) -> User or None:
		token = scope["url_route"]["kwargs"]["token"]
		token_obj = Token.objects.filter(key__exact=token).first()
		if not token_obj:
			return None
		return token_obj.user

	def connect(self):
		self.user = self.is_authenticated(self.scope)
		if not self.user:
			logging.critical("Authentication Refused")
			return
		async_to_sync(self.channel_layer.group_add)("general", self.channel_name)
		self.accept()
		self.send(f"{self.user.username} just connected to general channel")

	def websocket_receive(self, data):
		data = json.loads(data["text"])
		async_to_sync(self.channel_layer.group_send)(
			"general", {"type": "notify", "data": json.dumps(data)}
		)

	def notify(self, event):
		self.send(text_data=event["data"])

	def disconnect(self, code):
		super().disconnect(code)


class PrivateConsumer(WebsocketConsumer):
	"""
	This namespace handles all connections to personal channels, messages sent only to users themselves
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.user = None
		self.chat = None

	@staticmethod
	def is_authenticated(scope) -> User or None:
		token = scope["url_route"]["kwargs"]["token"]
		token_obj = Token.objects.filter(key__exact=token).first()
		if not token_obj:
			return None
		return token_obj.user

	def connect(self):
		self.user = self.is_authenticated(self.scope)
		if not self.user:
			logging.critical("Authentication Refused")
			self.close()
			return
		async_to_sync(self.channel_layer.group_add)(str(self.user), self.channel_name)
		self.accept()
		self.send(f"{self.user.username} just connected to private channel")

	def websocket_receive(self, data):
		data = json.loads(data["text"])
		async_to_sync(self.channel_layer.group_send)(
			str(self.user), {"type": "notify", "data": json.dumps(data)}
		)

	def notify(self, event):
		self.send(text_data=event["data"])

	def disconnect(self, code):
		super().disconnect(code)
