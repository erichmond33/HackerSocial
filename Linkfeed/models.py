from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
   pass

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField(blank=True)
    likes = models.TextField(default="0")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} : {self.user.username} : {self.user.id} {self.body} : {self.likes} : {self.timestamp}"

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user.id,
            "user_name": self.user.username,
            "body": self.body,
            "likes": self.likes,
            "timestamp": self.timestamp.strftime("%b %d %Y, %I:%M %p"),
        }

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    follower = models.ManyToManyField(
        User, blank=True, related_name="following_users")
    following = models.ManyToManyField(
        User, blank=True, related_name="follower_users")

    def __str__(self):
        return f"{self.user.username} : Followers = {self.follower.count()} : Following = {self.following.count()}"
