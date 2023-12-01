from rest_framework import serializers
from rest_framework.authtoken.models import Token

from core.helpers import send_ws_to_general, send_ws_to_chat
from core.models import User, ChatRoom, ChatMessage, ChatAttachment


class SignupSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ("first_name", "last_name", "email", "username", "password")

	def create(self, validated_data):
		user = User.objects.create_user(**validated_data)
		send_ws_to_general(user=user, event="NEW USER", data=UserSerializer(user).data)
		return user


class LoginSerializer(serializers.Serializer):
	username = serializers.CharField()
	password = serializers.CharField()

	def validate(self, attrs):
		user = User.objects.filter(username__iexact=attrs.pop('username')).first()
		if not user:
			raise serializers.ValidationError(detail="You dont have an account with us")
		if not user.check_password(attrs.pop('password')):
			raise serializers.ValidationError(detail="Invalid credential")
		attrs['user'] = user
		return attrs

	def create(self, validated_data):
		user = validated_data.pop("user")
		token, _ = Token.objects.get_or_create(user=user)
		send_ws_to_general(user=user, event="LOGGED IN", data=UserSerializer(user).data)
		return dict(token=token.key)


class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ("id", "first_name", "last_name", "username", "profile_picture")


class ChatRoomListSerializer(serializers.ModelSerializer):
	class Meta:
		model = ChatRoom
		fields = ("id", "name", "description")


class ChatRoomSerializer(serializers.ModelSerializer):
	admins = UserSerializer(many=True)
	members = UserSerializer(many=True)
	members_count = serializers.SerializerMethodField()

	class Meta:
		model = ChatRoom
		fields = "__all__"

	def get_members_count(self, obj):
		return obj.members.count()


class CreateChatRoomSerializer(serializers.ModelSerializer):
	class Meta:
		model = ChatRoom
		fields = ("name", "description", "maximum_members")

	def validate(self, attrs):
		user = self.context.get("user")
		if self.instance and attrs['maximum_members'] < self.instance.members.count():
			raise serializers.ValidationError(
				detail="The members count cannot be less than number of members in the room")
		if self.instance and not self.instance.admins.filter(id=user.id).exists():
			raise serializers.ValidationError(detail="Only admins are allowed to update room")
		return attrs

	def create(self, validated_data):
		user = self.context.get("user")
		chat_room = super(CreateChatRoomSerializer, self).create(validated_data)
		chat_room.members.add(user)
		chat_room.admins.add(user)
		chat_room.save()
		send_ws_to_general(user=user, event="NEW CHATROOM", data=ChatRoomListSerializer(chat_room).data)
		return chat_room

	def update(self, instance, validated_data):
		user = self.context.get("user")
		chat_room = super(CreateChatRoomSerializer, self).update(instance, validated_data)
		send_ws_to_general(user=user, event="UPDATE CHATROOM", data=ChatRoomListSerializer(chat_room).data)
		return chat_room


class ChatAttachments(serializers.ModelSerializer):
	file = serializers.SerializerMethodField()
	file_type = serializers.SerializerMethodField()

	class Meta:
		model = ChatAttachment
		fields = ("id", "file", "file_type")

	def get_file(self, obj):
		return obj.file

	def get_file_type(self, obj):
		return obj.file_type


class ChatMessageSerializer(serializers.ModelSerializer):
	attachments = serializers.SerializerMethodField()
	sender = UserSerializer(read_only=True)
	viewers_count = serializers.SerializerMethodField()
	viewed = serializers.SerializerMethodField()

	class Meta:
		model = ChatMessage
		fields = "__all__"

	def get_attachments(self, obj):
		return ChatAttachments(obj.attachments(), many=True).data

	def get_viewers_count(self, obj):
		return obj.viewers.count()

	def get_viewed(self, obj):
		user = self.context.get("user")
		if not user:
			return None
		return obj.viewed(user.id)


class ChatMessageListSerializer(ChatMessageSerializer):
	viewers = None


class CreateMessageSerializer(serializers.Serializer):
	chat = serializers.PrimaryKeyRelatedField(queryset=ChatRoom.objects.all())
	text = serializers.CharField(default=None)
	file = serializers.FileField()

	def validate(self, attrs):
		attrs["files"] = self.context.get("files", list())
		if "file" in attrs:
			del attrs['file']
		user = self.context.get("user")
		if not attrs['chat'].members.filter(id=user.id).exists():
			raise serializers.ValidationError(detail="You are not a member of this group")
		if attrs['text'] == "" and not attrs["files"]:
			raise serializers.ValidationError(detail="message cannot be empty")
		attrs["sender"] = user
		return attrs

	def create(self, validated_data):
		user = self.context.get("user")
		files = validated_data.pop("files", list())
		message = ChatMessage.objects.create(chat_id=validated_data['chat'].id,
		                                     text=validated_data['text'],
		                                     sender_id=user.id)
		if not files:
			return message
		for file_attachment in files:
			picture = None
			audio = None
			video = None
			document = None
			if isinstance(file_attachment, str):
				file_attachment = files[file_attachment]
			content_type = file_attachment.content_type.split("/")[-1]
			if content_type in ("jpg", "jpeg", "gif", "png"):
				picture = file_attachment
			elif content_type in ("mp3", "ogg", "mpeg", "wav"):
				audio = file_attachment
			elif content_type in ("mp4", "3gp"):
				video = file_attachment
			else:
				document = file_attachment
			ChatAttachment.objects.create(
				message=message, picture=picture, audio=audio, video=video, document=document)
		send_ws_to_chat(user=user, chat_id=message.chat_id, event="NEW MESSAGE",
		                data=ChatMessageSerializer(message).data)
		return message


class ChatActionSerializer(serializers.Serializer):
	chat = serializers.PrimaryKeyRelatedField(queryset=ChatRoom.objects.all())
	action = serializers.ChoiceField(choices=["join", "leave"])

	def validate(self, attrs):
		user = self.context.get("user")
		is_member = attrs['chat'].members.filter(id=user.id).exists()
		if is_member and attrs['action'] == "join":
			raise serializers.ValidationError(detail="You are already a member of this chat")
		if not is_member and attrs['action'] == "leave":
			raise serializers.ValidationError(detail="You are not a member of this chat")
		if attrs['chat'].members.count() == attrs['chat'].maximum_members:
			raise serializers.ValidationError(detail="This group is full")
		return attrs

	def create(self, validated_data):
		user = self.context.get("user")
		chatroom = validated_data.pop("chat")
		action = validated_data.pop("action")
		event = ""
		if action == "join":
			chatroom.members.add(user)
			event = "NEW MEMBER"
		elif action == "leave":
			chatroom.members.remove(user)
			chatroom.admins.remove(user)
			event = "MEMBER EXIT"
		chatroom.save()
		# ensure that a chatroom admin members list is not empty
		if chatroom.admins.count() == 0 and chatroom.members.count() > 0:
			chatroom.admins.add(chatroom.members.first())
			chatroom.save()
		send_ws_to_chat(user=chatroom.admins.first(), chat_id=chatroom.id, event=event,
		                data=UserSerializer(user).data)
		return chatroom
