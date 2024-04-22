from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    pass

class RSSFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link = models.URLField()

    def __str__(self):
        return f"{self.user.username}'s RSS Feed: {self.link}"

class ImportedRSSFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link = models.URLField()

    def __str__(self):
        return f"Imported RSS Feed for {self.user.username}: {self.link}"
    
from django.db import models
import datetime

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(blank=True, max_length=255)
    body = models.URLField(blank=True, null=True)
    likes = models.ManyToManyField(User, related_name="blog_posts")
    timestamp = models.DateTimeField(auto_now_add=False, null=True)
    is_rss_feed_post = models.BooleanField(default=False)
    is_imported_rss_feed_post = models.BooleanField(default=False)
    imported_rss_feed = models.ForeignKey(ImportedRSSFeed, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    repost_count = models.IntegerField(default=0)  # New field for repost count

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now()
        super(Post, self).save(*args, **kwargs)

    def total_comments(self):
        return self.comments.count()
    
    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.id} : {self.user.username} : id={self.user.id} : {self.title} : {self.body} : {self.likes} : {self.timestamp}"

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user.id,
            "user_name": self.user.username,
            "body": self.body,
            "likes": self.likes,
            "timestamp": self.timestamp.strftime("%b %d %Y, %I:%M %p"),
        }



class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)

    def __tr__(self):
        return f"{self.user.username}"

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    body = models.TextField()
    likes = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} : {self.post.title} : {self.body} : {self.timestamp}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    follower = models.ManyToManyField(User, blank=True, related_name="follower_user")
    following = models.ManyToManyField(User, blank=True, related_name="following_user")

    def __str__(self):
        return f"{self.user.username} : Followers = {self.follower.count()} : {self.link} : Following = {self.following.count()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class UserCSS(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link = models.URLField()  # Store the CSS content directly

    def __str__(self):
        return f"Custom CSS Style for {self.user.username}"

from django.db import models
from django.contrib.auth import get_user_model  # Import the correct function

class AllowedDomain(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)  # Use get_user_model()
    domain = models.CharField(max_length=255, unique=True) 

    def __str__(self):
        return f"{self.user.username} - {self.domain}"

