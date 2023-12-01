from django.contrib.auth.models import AbstractUser
from django.db import models

from core.helpers import send_ws_to_chat


# Create your models here.

class User(AbstractUser):
	first_name = models.CharField(max_length=200)
	last_name = models.CharField(max_length=200)
	email = models.EmailField(unique=True)
	profile_picture = models.ImageField(upload_to="profile_pics")

	def __str__(self):
		return f"user_{self.id}"


class ChatRoom(models.Model):
	name = models.CharField(default="", max_length=100, unique=True)
	description = models.CharField(default="", max_length=100)
	members = models.ManyToManyField("User", blank=True, related_name="members")
	maximum_members = models.PositiveSmallIntegerField(default=100)
	admins = models.ManyToManyField("User", blank=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"chat_{self.id}"


class ChatMessage(models.Model):
	chat = models.ForeignKey("ChatRoom", on_delete=models.CASCADE)
	text = models.CharField(max_length=300)
	viewers = models.ManyToManyField("User", blank=True, related_name="viewers")
	sender = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
	time_sent = models.DateTimeField(auto_now_add=True)

	def attachments(self):
		return ChatAttachment.objects.filter(message=self)

	def view(self, user):
		self.viewers.add(user)
		self.save()
		return

	def viewed(self, user_id):
		return self.viewers.filter(id=user_id).exists()


class ChatAttachment(models.Model):
	message = models.ForeignKey("ChatMessage", on_delete=models.CASCADE)
	picture = models.ImageField(upload_to="root/pictures", default=None, null=True)
	audio = models.FileField(upload_to="root/audios", default=None, null=True)
	document = models.FileField(upload_to="root/documents", default=None, null=True)
	video = models.FileField(upload_to="root/videos", default=None)

	@property
	def file(self):
		if self.video:
			return self.video.url
		elif self.picture:
			return self.picture.url
		elif self.audio:
			return self.audio.url
		return self.document.url

	@property
	def file_type(self):
		return "picture" if self.picture else "video" if self.video else "audio" if self.audio else "document"
