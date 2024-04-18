from sqlite3 import IntegrityError
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse,HttpResponseForbidden, JsonResponse, HttpResponseBadRequest

from django.urls import reverse

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import User, Post, Profile, Comment, PostLike

from django.http import Http404
from .forms import RSSFeedForm 
from .models import RSSFeed
import feedparser
from .forms import ImportedRSSFeedForm
from .models import ImportedRSSFeed

from django.db.models import Q


def index(request):
    if request.user.is_authenticated:
        return redirect('profile', username=request.user.username)
    else:
        return redirect('login')
    
def landing(request):
    return render(request, "Linkfeed/index.html")

@login_required
def current_user_profile(request):
    user = request.user
    return redirect('profile', username=user.username)

def profile(request, username):
    user = User.objects.get(username=username)
    posts = Post.objects.filter(user=user)
    profile = Profile.objects.get(user=user)

    # Check if we are following them
    following = False
    if request.user.is_authenticated:
        if request.user in profile.follower.all():
            following = True

    # Order posts reverse chronologically
    posts = posts.order_by("timestamp").all()

    return render(request, "Linkfeed/profile.html", {"posts": posts, "profile": profile, "following": following})

@login_required
def current_user_feed(request):
    user = request.user
    return redirect('feed', username=user.username)
    
def feed(request, username):
    user = User.objects.get(username=username)
    profile = Profile.objects.get(user=user)
    following = profile.following.all()
    posts = Post.objects.filter(user__in=following)
    posts = posts.order_by("timestamp").all()
    
    return render(request, "Linkfeed/feed.html", {"posts": posts, "profile": profile})

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Pass the authentication token to the session
            # request.session['auth_token'] = request.session.session_key
            # return HttpResponseRedirect(reverse("index"))
            return redirect('profile', username=username)
        else:
            return render(request, "Linkfeed/login.html", {
                "message": "Invalid credentials."
            })
    return render(request, "Linkfeed/login.html")



from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmation = request.POST.get("confirmation")

        # Ensure password matches confirmation
        if password != confirmation:
            return render(request, "Linkfeed/register.html", {
                "message": "Passwords must match."
            })

        try:
            # Attempt to create new user
            user = User.objects.create_user(username, email, password)
            # Log in the user
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        except IntegrityError as e:
            if 'unique constraint' in str(e).lower() and 'username' in str(e).lower():
                # Username already exists
                return render(request, "Linkfeed/register.html", {
                    "message": "Username already exists."
                })
            else:
                # Other IntegrityError, log and render generic error message
                logger.error("IntegrityError occurred during user registration: %s", e)
                return render(request, "Linkfeed/register.html", {
                    "message": "An error occurred during registration. Please try again later."
                })

    else:
        return render(request, "Linkfeed/register.html")


        
def logout_view(request):
    logout(request)
    return render(request, "Linkfeed/login.html", {
        "message": "Logged out."
    })



def post(request, post_id):
    if not request.user.is_authenticated:
        #if not return to login page
        return HttpResponseRedirect(reverse("login"))
    else:
        try:
            stuff = get_object_or_404(Post, id=post_id)
            total_likes = stuff.total_likes()
            liked = False
            if stuff.likes.filter(id=request.user.id).exists():
                liked = True
            post = get_object_or_404(Post, id=post_id)
            comments = Comment.objects.filter(post=post)  # Fetch comments associated with the post
            return render(request, "Linkfeed/post.html", {"post": post, "comments": comments, 'stuff': stuff, 'total_likes': total_likes, 'liked': liked})
        except Http404:
            return HttpResponse("404 - Post Not Found", status=404)
        

def add_comment(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        comment_body = request.POST.get("comment_body")
        # Create a new comment object and save it to the database
        comment = Comment.objects.create(user=request.user, post=post, body=comment_body)
        # Redirect to the post detail page after adding the comment
        return redirect("post", post_id=post_id)
    # Handle other HTTP methods if necessary

from django.shortcuts import redirect
from django.contrib import messages

def delete_comment(request, comment_id):
    if request.method == "POST":  # Change to POST method
        comment = get_object_or_404(Comment, id=comment_id)
        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Check if the user is the owner of the comment or the owner of the post
            if comment.user == request.user or comment.post.user == request.user:
                comment.delete()
                # Redirect to the previous page
                return redirect(request.META.get('HTTP_REFERER', '/'))
            else:
                # Handle unauthorized deletion
                messages.error(request, 'You are not authorized to delete this comment.')
        else:
            # Handle authentication error
            messages.error(request, 'You must be logged in to delete a comment.')
    # If the request method is not POST or deletion fails, redirect to the previous page
    return redirect(request.META.get('HTTP_REFERER', '/'))





def delete_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        # Check if the user is authenticated and is the owner of the post
        if request.user.is_authenticated and post.user == request.user:
            post.delete()
            # Redirect back to the same page
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('profile')))
        else:
            # Handle unauthorized deletion
            return HttpResponseForbidden("You are not authorized to delete this post.")

def edit_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        # Check if the user is authenticated and is the owner of the post
        if request.user.is_authenticated and post.user == request.user:
            # Update the post title and body with the new values
            post.title = request.POST.get("post_title")
            post.body = request.POST.get("post_body")
            post.save()
            # Redirect back to the post detail page after editing the post
            return redirect("post", post_id=post_id)
        else:
            # Handle unauthorized edits
            return HttpResponseForbidden("You are not authorized to edit this post.")
    # Handle other HTTP methods if necessary
        

def create_post(request):
    if request.method == "POST":
        title = request.POST.get('title')
        body = request.POST.get('body')
        # Create a new post
        new_post = Post.objects.create(user=request.user, title=title, body=body)
        # Redirect to the profile page after creating the post
        return HttpResponseRedirect(reverse("profile"))
    else:
        return render(request, "Linkfeed/create_post.html")
    


@login_required
def like_view(request, pk):
    # Assuming your Post model and like logic remains the same
    post = get_object_or_404(Post, id=request.POST.get('post_id'))

    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)

    # Get the referring URL
    referring_url = request.META.get('HTTP_REFERER')

    # Append the pk parameter to the referring URL
    redirect_url = f"{referring_url}?pk={pk}" if referring_url else reverse('index')

    # Redirect to the modified URL
    return HttpResponseRedirect(redirect_url)



@login_required
def followers_view(request, username):
    # Get the profile of the user whose followers you want to see
    user_profile = get_object_or_404(Profile, user__username=username)
    # Get the followers of the user
    followers = user_profile.follower.all()
    return render(request, 'Linkfeed/followers.html', {'followers': followers})


@login_required
def following_view(request, username):
    # Get the profile of the user whose following you want to see
    user_profile = get_object_or_404(Profile, user__username=username)
    # Get the Linkfeed followed by the user
    following = user_profile.following.all()
    return render(request, 'Linkfeed/following.html', {'following': following})


@login_required
def follow_view(request, username):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    else:
        # Retrieve the profile of the user to follow
        profile_to_follow = get_object_or_404(Profile, user__username=username)
        profile = get_object_or_404(Profile, user=request.user)

        # Check if the requested profile is the profile of the logged-in user
        if profile_to_follow.user == request.user:
            return redirect('current_user_profile')
        else:
            # Check if the logged-in user is already following the profile
            if request.user in profile_to_follow.follower.all():
                # User is already following, so unfollow
                profile_to_follow.follower.remove(request.user)
                profile.following.remove(profile_to_follow.user)  # Remove profile from user's following
            else:
                # User is not following, so follow
                profile_to_follow.follower.add(request.user)
                profile.following.add(profile_to_follow.user)  # Add profile to user's following

        # Redirect to the profile of the user being followed or unfollowed
        return HttpResponseRedirect(reverse('profile', args=[username]))
    
@login_required
def follow_or_unfollow(request, username):
    # Retrieve the profile of the user to follow
    profile_to_follow = Profile.objects.get(user__username=username)
    profile = Profile.objects.get(user=request.user)

    # Check if the logged-in user is already following the profile
    if request.user in profile_to_follow.follower.all():
        # User is already following, so unfollow
        profile_to_follow.follower.remove(request.user)
        profile.following.remove(profile_to_follow.user)
    else:
        # User is not following, so follow
        profile_to_follow.follower.add(request.user)
        profile.following.add(profile_to_follow.user)

    # Render the same page after following or unfollowing
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('profile')))

def mirror_rss_feed(request):
    form = RSSFeedForm(request.POST or None)
    user = request.user

    if request.method == 'POST':
        if form.is_valid():
            rss_feed_link = form.cleaned_data['link']
            # Check if the user already has an RSS feed stored
            existing_feed = RSSFeed.objects.filter(user=user).first()
            if existing_feed:
                # Delete all RSS feed posts created from the previous RSS feed link
                Post.objects.filter(user=user, is_rss_feed_post=True).delete()
                # Update the existing RSS feed link
                existing_feed.link = rss_feed_link
                existing_feed.save()
            else:
                # Create a new RSS feed entry
                RSSFeed.objects.create(user=user, link=rss_feed_link)

            # Redirect to the same page to avoid resubmission
            return HttpResponseRedirect(request.path_info)

    # Retrieve the updated list of RSS feeds for the user
    rss_feed = RSSFeed.objects.filter(user=request.user).first()
    if rss_feed:
        # Delete all RSS feed posts created from the previous RSS feed link
        Post.objects.filter(user=user, is_rss_feed_post=True).delete()

        feed = feedparser.parse(rss_feed.link)
        entries = feed.entries
        
        # Iterate through each entry in reverse order and create a post
        for entry in (entries):
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')  # You can change this to get other fields like summary
            # Create a new post with is_rss_feed_post=True
            new_post = Post.objects.create(user=user, title=title, body=body, timestamp=entry.get('published_parsed'), is_rss_feed_post=True)
    else:
        entries = []  # Handle case where RSS feed is not available

    return redirect('profile')








def imported_rss_feed(request):
    form = ImportedRSSFeedForm(request.POST or None)
    user = request.user

    if request.method == 'POST':
        if form.is_valid():
            rss_feed_link = form.cleaned_data['link']
            existing_feed = ImportedRSSFeed.objects.filter(user=user, link=rss_feed_link).exists()
            if not existing_feed:
                new_imported_feed = ImportedRSSFeed.objects.create(user=user, link=rss_feed_link)
                feed = feedparser.parse(rss_feed_link)
                entries = feed.entries
                for entry in reversed(entries):
                    title = entry.get('title', 'No Title')
                    body = entry.get('link', 'No Link')
                    # Create a new post and associate it with the imported RSS feed
                    new_post = Post.objects.create(user=user, title=title, body=body, is_imported_rss_feed_post=True, imported_rss_feed=new_imported_feed)
            return HttpResponseRedirect(request.path_info)

    user_imported_rss_feeds = ImportedRSSFeed.objects.filter(user=user)
    for imported_feed in user_imported_rss_feeds:
        feed = feedparser.parse(imported_feed.link)
        entries = feed.entries
        for entry in reversed(entries):
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')
            new_post = Post.objects.create(user=user, title=title, body=body, timestamp=entry.get('published_parsed'), is_imported_rss_feed_post=True, imported_rss_feed=imported_feed)

    return redirect('feed')



def delete_imported_feed(request, feed_id):
    if request.method == "DELETE":
        feed = get_object_or_404(ImportedRSSFeed, id=feed_id, user=request.user)
        # Check if the user is authenticated and is the owner of the feed
        if feed.user == request.user:
            feed.delete()
            # Return a JSON response indicating success
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('feed')))
        else:
            # Return a forbidden response if the user is not the owner of the feed
            return HttpResponseForbidden("You are not authorized to delete this feed.")


def refresh_mirrored_rss_feed(request):
    user = request.user
    rss_feed = RSSFeed.objects.filter(user=user).first()

    if rss_feed:
        feed = feedparser.parse(rss_feed.link)
        entries = feed.entries

        for entry in entries:
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')

            # Check if a post with the same title and body already exists as a mirrored RSS feed post
            if not Post.objects.filter(user=user, title=title, body=body, is_rss_feed_post=True).exists():
                # Create a new post with is_rss_feed_post=True
                new_post = Post.objects.create(user=user, title=title, body=body, is_rss_feed_post=True)
    else:
        entries = []

    return redirect('profile')


def refresh_imported_rss_feed(request):
    user = request.user
    imported_rss_feeds = ImportedRSSFeed.objects.filter(user=user)

    for imported_feed in imported_rss_feeds:
        feed = feedparser.parse(imported_feed.link)
        entries = feed.entries

        for entry in entries:
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')

            # Check if a post with the same title and body already exists as an imported RSS feed post
            if not Post.objects.filter(user=user, title=title, body=body, is_imported_rss_feed_post=True, imported_rss_feed=imported_feed).exists():
                # Create a new post associated with the imported RSS feed
                new_post = Post.objects.create(user=user, title=title, body=body, is_imported_rss_feed_post=True, imported_rss_feed=imported_feed)

    return redirect('feed')


def landing(request):
    return render(request, 'Linkfeed/landingpage.html')