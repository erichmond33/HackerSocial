from django.db import models
import datetime
from django.contrib.auth.models import User

class RSSFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link = models.URLField()

    def __str__(self):
        return f"{self.user.username}'s RSS Feed: {self.link}"

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(blank=True, max_length=255)
    body = models.URLField(blank=True, null=True)
    likes = models.ManyToManyField(User, related_name="blog_posts")
    timestamp = models.DateTimeField(auto_now_add=False, null=True)
    is_rss_feed_post = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now()
        super(Post, self).save(*args, **kwargs)

    def total_comments(self):
        return self.comments.count()
    
    def total_likes(self):
        return self.likes.count()
    
    def only_domain(self):
        return self.body.replace("http://", "").replace("https://", "").split("/")[0]

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

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments", null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    display_name = models.CharField(max_length=255)
    body = models.TextField()
    likes = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.IntegerField(default=0)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} : {self.post.title} : {self.body} : {self.timestamp}"
    
    def save(self, *args, **kwargs):
        if self.parent_comment:
            self.level = self.parent_comment.level + 1
        if not self.display_name:
            self.display_name = self.user.profile.display_name
        super().save(*args, **kwargs)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    follower = models.ManyToManyField(User, blank=True, related_name="follower_user")
    following = models.ManyToManyField(User, blank=True, related_name="following_user")
    domain = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} : Followers = {self.follower.count()}  : Following = {self.following.count()}"
    
    def formatCount(self, followers_or_following):
        if followers_or_following == "followers":
            # Retrieve the follower count
            count = self.follower.count()
        elif followers_or_following == "following":
            # Retrieve the following count
            count = self.following.count()

        # Determine the appropriate format based on the number of followers
        if count < 10:
            formatted = f"{count}"  # Three spaces for single digit numbers
        elif count < 100:
            formatted = f"{count}"  # Two spaces for two digit numbers
        elif count < 1000:
            formatted = f"{count}"  # One space for three digit numbers
        elif count < 10000:
            formatted = f"{count}"  # Exact count for 1000-9999
        elif count < 100000:
            formatted = f"{count // 1000}k"  # Thousands without decimal for 10k-99k
        elif count < 1000000:
            formatted = f"{count / 1000:.1f}k"  # Thousands with one decimal for 100k-999k
        elif count < 10000000:
            formatted = f"{count // 1000000}m"  # Millions without decimal for 1m-9m
        else:
            formatted = f"{count / 1000000:.1f}m"  # Millions with one decimal for 10m and more

        return formatted

    def strippedDomainLink(self):
        return self.domain.replace("http://", "").replace("https://", "").strip("/")