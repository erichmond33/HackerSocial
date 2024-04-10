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
    
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(blank=True, max_length=255)
    body = models.URLField(blank=True, null=True)
    likes = models.ManyToManyField(User, related_name="blog_posts")
    timestamp = models.DateTimeField(auto_now_add=True)
    is_rss_feed_post = models.BooleanField(default=False)
    is_imported_rss_feed_post = models.BooleanField(default=False)  # New field
    imported_rss_feed = models.ForeignKey(ImportedRSSFeed, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")

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
    body = models.TextField()
    likes = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} : {self.post.title} : {self.body} : {self.timestamp}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # website = models.URLField(blank=True, null=True)
    follower = models.ManyToManyField(User, blank=True, related_name="follower_user")
    following = models.ManyToManyField(User, blank=True, related_name="following_user")

    def __str__(self):
        return f"{self.user.username} : Followers = {self.follower.count()} : Following = {self.following.count()}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
