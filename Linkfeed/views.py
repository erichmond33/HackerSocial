from sqlite3 import IntegrityError
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound, HttpResponseRedirect, HttpResponse,HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import *
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.http import Http404
import feedparser
import datetime
import dateutil.parser 
from django.db.models import Q
from datetime import datetime
from django.db.models import Count
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt


def index(request):
    if request.user.is_authenticated:
        return redirect('profile', username=request.user.username)
    else:
        return render(request, "Linkfeed/login.html")
    
def landing(request):
    return render(request, "Linkfeed/landingpage.html")

@login_required
def current_user_profile(request):
    return profile(request, request.user.username)



def profile(request, username):
    user = User.objects.get(username=username)
    posts = Post.objects.filter(user=user)
    profile = Profile.objects.get(user=user)
    domain = profile.domain
    
    profile.link = domain
    profile.stripped_link = profile.strippedDomainLink()

    profile.following_count = profile.formatCount("following")
    profile.followers_count = profile.formatCount("followers")

    # Order posts reverse chronologically
    posts = Post.objects.filter(user=user).annotate(total_comments=Count('comments')).order_by('-timestamp')

    # Check if the user has liked each post
    for post in posts:
        post.liked = post.likes.filter(id=user.id).exists()

    return render(request, "Linkfeed/profile.html", {"posts": posts, "profile": profile})


@login_required
def current_user_feed(request):
    return feed(request, request.user.username)

     
def feed(request, username):
    context = get_user_feed(request, username)
    return render(request, 'Linkfeed/feed.html', context)

def feed_rss_view(request, username):
    context = get_user_feed(request, username)
    response = render(request, 'Linkfeed/feed_rss.xml', context)
    response['Content-Type'] = 'application/xml'
    return response

def get_user_feed(request, username):
    user = User.objects.get(username=username)
    profile = Profile.objects.get(user=user)

    following_ids = profile.following.all().values_list('id', flat=True)
    posts = Post.objects.filter((Q(user__id__in=following_ids))).annotate(total_comments=Count('comments')).order_by('-timestamp')

    for post in posts:
        post.liked = post.likes.filter(id=user.id).exists()

    for post in posts:
        post.liked = post.likes.filter(id=request.user.id).exists()

    context = {'posts': posts, 'profile': profile}

    return context

def login_view(request):
    if request.method == "POST":
        email_or_username = request.POST["email_or_username"]
        password = request.POST["password"]
        print(email_or_username, password)
        # Check if the input is an email
        if '@' in email_or_username:
            try:
                user = User.objects.get(email=email_or_username)
                username = user.username
            except User.DoesNotExist:
                username = email_or_username
        else:
            username = email_or_username
        
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            # Pass the authentication token to the session
            # request.session['auth_token'] = request.session.session_key
            # return HttpResponseRedirect(reverse("index"))
            return redirect('profile', username=user.username)
        else:
            return render(request, "Linkfeed/login.html", {
                "message": "Invalid credentials."
            })
    elif request.method == "GET":
        if request.user.is_authenticated:
            return redirect('profile', username=request.user.username)
        return render(request, "Linkfeed/login.html")



from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        display_name = username
        link = request.POST.get("link")
        stripped_link = link.split('//')[-1].split('/')[0] # Stripped link
        username = stripped_link
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmation = request.POST.get("confirmation")

        # Ensure password matches confirmation
        if password != confirmation:
            return render(request, "Linkfeed/register.html", {
                "message": "Passwords must match."
            })
        
        # Check if email is already used
        if User.objects.filter(email=email).exists():
            return render(request, "Linkfeed/register.html", {
                "message": "Email already used."
            })

        try:
            # Check if username is already taken
            username_taken = True
            while username_taken:
                try:
                    user = User.objects.get(username=username)
                    if user:
                        # Increment username i.e. username1, username2, username3
                        username = f"{stripped_link}{int(username[-1]) + 1 if username[-1].isdigit() else 1}"

                except User.DoesNotExist:
                    username_taken = False

            # Attempt to create new user
            user = User.objects.create_user(username, email, password)

            # Create a Profile instance with the link
            profile = Profile.objects.create(user=user, display_name=display_name, domain=link)

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

    elif request.method == "GET":
        if request.user.is_authenticated:
            return redirect('profile', username=request.user.username)
        return render(request, "Linkfeed/register.html")

def logout_view(request):
    logout(request)
    return render(request, "Linkfeed/login.html", {
        "message": "Logged out."
    })

def post(request, post_id):
    try:
        stuff = get_object_or_404(Post, id=post_id)
        # Get the profile of the user who created the post
        profile = Profile.objects.get(user=stuff.user)
        total_likes = stuff.total_likes()
        liked = False
        if stuff.likes.filter(id=request.user.id).exists():
            liked = True
        post = get_object_or_404(Post, id=post_id)
        comments = Comment.objects.filter(post=post, parent_comment=None)  # Fetch comments associated with the post
        add_level(comments)
        return render(request, "Linkfeed/post.html", {"post": post, "comments": comments, 'stuff': stuff, 'total_likes': total_likes, 'liked': liked, 'profile': profile, 'id': get_by_date_id(post)})
    except Http404:
        return HttpResponse("404 - Post Not Found", status=404)
    
def post_by_date(request, username, date):
    post_obj = by_date(request, username, date)
    return post(request, post_obj.id)

@csrf_exempt
@xframe_options_exempt
def comments_by_date(request, username, date):
    post_obj = by_date(request, username, date)
    comments = Comment.objects.filter(post=post_obj, parent_comment=None)
    add_level(comments)
    return render(request, 'Linkfeed/comment.html', {'post': post_obj, 'comments': comments})

def by_date(request, username, date):
    # Date format YYYY-MM-DD
    user = get_object_or_404(User, username=username)
    try:
        id = int(request.GET.get('id')) - 1
        post_obj = Post.objects.filter(user=user, timestamp__date=date).order_by('timestamp')[id]
    except:
        post_obj = Post.objects.filter(user=user, timestamp__date=date).order_by('timestamp').last()
    if post_obj:
        return post_obj
    else:
        return HttpResponseNotFound("Post not found")
    
def get_by_date_id(post_obj):
    # By date uses an id to differentiate between posts on the same day
    # This gets the correct id
    try:
        user = post_obj.user
        date = post_obj.timestamp.date()
        posts = Post.objects.filter(user=user, timestamp__date=date).order_by('timestamp')
        id = list(posts.values_list('id', flat=True)).index(post_obj.id)
        return id + 1
    except:
        return HttpResponseNotFound("Post not found")

def get_user_notifications(request, username):
    user = User.objects.get(username=username)
    profile = Profile.objects.get(user=user)
    notifications = Comment.objects.filter(post__user=user).order_by('-timestamp')
    context = {'notifications': notifications, 'profile': profile}
    return context

def notifications_view(request):
    context = get_user_notifications(request, request.user.username)
    return render(request, 'Linkfeed/notifications.html', context)

def notifications_rss_view(request, username):
    context = get_user_notifications(request, username)
    response = render(request, 'Linkfeed/notifications_rss.xml', context)
    response['Content-Type'] = 'application/xml'
    return response

def mark_notification_as_read(request, username):
    if request.method == 'POST':
        if request.user == User.objects.get(username=username):
            user = User.objects.get(username=username)
            notifications = Comment.objects.filter(post__user=user, read=False)
            for notification in notifications:
                notification.read = True
                notification.save()
            return JsonResponse({'message': 'Notifications marked as read'})
        else:
            return HttpResponseForbidden(JsonResponse({'message': 'You are not authorized to mark notifications as read'}))
    else:
        return HttpResponseBadRequest(JsonResponse({'message': 'Invalid request method'}))
        
def add_level(comments, level=0):
    for comment in comments:
        comment.level = level
        add_level(comment.replies.all(), level + 1)

@csrf_exempt
def add_comment(request, post_id):
    if request.method == "POST":
        post = Post.objects.get(id=post_id)
        comment_body = request.POST.get("body")
        guest_name = request.POST.get("display_name")
        # Create a new comment object and save it to the database
        if guest_name:
            Comment.objects.create(user=None, post=post, body=comment_body, display_name=guest_name)
        else:
            Comment.objects.create(user=request.user, post=post, body=comment_body)
        # Redirect back to where we were
        return redirect(request.META.get('HTTP_REFERER', '/'))

@csrf_exempt
def reply_comment(request, comment_id):
    if request.method == "POST":
        parent_comment = get_object_or_404(Comment, id=comment_id)
        post = parent_comment.post
        comment_body = request.POST.get("body")
        guest_name = request.POST.get("display_name")
        if guest_name:
            Comment.objects.create(user=None, post=post, body=comment_body, parent_comment=parent_comment, display_name=guest_name)
        else:
            Comment.objects.create(user=request.user, post=post, body=comment_body, parent_comment=parent_comment)
        return redirect(request.META.get('HTTP_REFERER', '/'))
    else:
        return HttpResponseBadRequest("Invalid request method")

from django.shortcuts import redirect
from django.contrib import messages

@login_required
def delete_comment(request, comment_id):
    if request.method == "POST" or request.method == "GET":
        comment = get_object_or_404(Comment, id=comment_id)
        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Check if the user is the owner of the comment or the owner of the post
            if comment.user == request.user or comment.post.user == request.user:
                comment.delete()
                return redirect("post", post_id=comment.post.id)
            else:
                # Handle unauthorized deletion
                messages.error(request, 'You are not authorized to delete this comment.')
        else:
            # Handle authentication error
            messages.error(request, 'You must be logged in to delete a comment.')
    # If the request method is not POST or deletion fails, redirect to the previous page
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def edit_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id)
        if request.user.is_authenticated and comment.user == request.user:
            comment.body = request.POST.get("body")
            comment.save()
            return redirect("post", post_id=comment.post.id)
        else:
            return HttpResponseForbidden("You are not authorized to edit this post.")
    elif request.method == "GET":
        profile = Profile.objects.get(user=request.user)
        comment = get_object_or_404(Comment, id=comment_id)
        if request.user == comment.user:
            return render(request, "Linkfeed/edit_comment.html", {"comment": comment, "profile": profile})
        else:
            return HttpResponseForbidden("You are not authorized to edit this post.")

@login_required
def delete_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        # Check if the user is authenticated and is the owner of the post
        if request.user.is_authenticated and post.user == request.user:
            post.delete()
            return redirect("profile")
        else:
            # Handle unauthorized deletion
            return HttpResponseForbidden("You are not authorized to delete this post.")

@login_required
def edit_post(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        # Check if the user is authenticated and is the owner of the post
        if request.user.is_authenticated and post.user == request.user:
            # Update the post title and body with the new values
            post_title = request.POST.get("title")
            if post_title:
                post.title = post_title
            post_body = request.POST.get("body")
            if post_body:
                post.body = post_body
            post.save()
            # Redirect back to the post detail page after editing the post
            return redirect("post", post_id=post_id)
        else:
            # Handle unauthorized edits
            return HttpResponseForbidden("You are not authorized to edit this post.")
    elif request.method == "GET":
        profile = Profile.objects.get(user=request.user)
        post = get_object_or_404(Post, id=post_id)
        if request.user == post.user:
            return render(request, "Linkfeed/edit_post.html", {"post": post, "profile": profile})
        else:
            return HttpResponseForbidden("You are not authorized to edit this post.")


@login_required  # Ensure the user is logged in 
def edit_profile(request):
    if request.method == "POST":
        # Get the current user's profile instance
        profile = get_object_or_404(Profile, user=request.user)

        # Update the link
        new_link = request.POST.get('link')
        if new_link:
            profile.domain = new_link
            profile.save()

        # Update the display_name
        new_display_name = request.POST.get('display_name')
        if new_display_name:
            profile.display_name = new_display_name
            profile.save()

        # Update the username
        new_username = request.POST.get('username')
        if new_username:
            # Check if the new username is already taken
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                # Handle the case where the username is already taken
                # You can display an error message or take any other appropriate action
                error_message = "The username is already taken. Please choose a different one."
                # Pass the error message to the template context
                context = {'error_message': error_message}
                return HttpResponseBadRequest("The username is already taken. Please choose a different one.")
            else:
                request.user.username = new_username
                request.user.save()

        # Update the email
        new_email = request.POST.get('email')
        if new_email:
            request.user.email = new_email
            request.user.save()

        # Redirect to the profile page after editing
        return redirect('profile') 
    else:
        profile = get_object_or_404(Profile, user=request.user)
        return render(request, 'Linkfeed/edit_profile.html', {'profile': profile})

@login_required
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
def like_view(request, post_id):
    if request.method == 'POST':
        post = Post.objects.get(id=post_id)
        user = request.user
        liking = True
        if user in post.likes.all():
            post.likes.remove(user)
            liking = False
        else:
            post.likes.add(user)
            liking = True
        return JsonResponse({'total_likes': post.total_likes(), 'liking': liking})
    else:
        return HttpResponseBadRequest("Invalid request method")


@login_required
def followers_view(request, username):
    profile = get_object_or_404(Profile, user__username=username)
    followers = profile.follower.all()
    return render(request, 'Linkfeed/followers.html', {'followers': followers, "profile" : profile})


@login_required
def following_view(request, username):
    profile = get_object_or_404(Profile, user__username=username)
    # Get the Linkfeed followed by the user
    following = profile.following.all()
    return render(request, 'Linkfeed/following.html', {'following': following, "profile" : profile})
    
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

def parse_timestamp(entry):
    timestamp_str = {
                'published': entry.get('published'),
                'pubDate': entry.get('pubDate'),
                'dc:date': entry.get('dc:date'),
                'date' : entry.get('date'),
                'atom:published': entry.get('atom:published'),
                'dc:created': entry.get('dc:created')
            }
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',  # Original format
        '%a, %d %b %Y %H:%M:%S %Z',  # pubDate format
        '%Y-%m-%d'  # Added for parsing only dates
    ]

    if isinstance(timestamp_str, str):
        # Direct Parsing Attempt for strings:
        for fmt in formats:
            try:
                # Attempt to parse as datetime first 
                if fmt == '%Y-%m-%dT%H:%M:%S%z':
                    return datetime.strptime(timestamp_str, fmt)
                elif fmt == '%Y-%m-%d':
                    return datetime.strptime(timestamp_str, fmt).date()
                else:
                    return dateutil.parser.parse(timestamp_str) 
            except ValueError:
                continue  # Try other formats

    elif isinstance(timestamp_str, dict):
        # Iterate over potential field names (if direct parsing failed)
        for field_name in timestamp_str:
            timestamp = timestamp_str.get(field_name)
            if timestamp:
                for fmt in formats:
                    try:
                        # Attempt to parse as datetime first 
                        if fmt == '%Y-%m-%dT%H:%M:%S%z':
                            return datetime.strptime(timestamp, fmt)
                        elif fmt == '%Y-%m-%d':
                            return datetime.strptime(timestamp, fmt).date()
                        else:
                            return dateutil.parser.parse(timestamp) 
                    except ValueError:
                        continue  # Try other formats

    return None  # Parsing unsuccessful

@login_required
def rss(request):
    profile = Profile.objects.get(user=request.user)
    rss_feeds = RSSFeed.objects.filter(user=request.user)
    return render(request, 'Linkfeed/rss.html', {'profile' : profile, 'rss_feeds': rss_feeds})

@login_required
def mirror_rss_feed(request):
    if request.method == 'POST':
        rss_link = request.POST.get('link')
        user = request.user

        if RSSFeed.objects.filter(user=user, link=rss_link).exists():
            return HttpResponseBadRequest("RSS Feed already exists")

        rss_feed = RSSFeed.objects.create(user=user, link=rss_link)
        
        refresh_mirrored_rss_feed(user, rss_feed)

    return redirect('profile')

def refresh_mirrored_rss_feed_view(request):
    user = request.user
    rss_feeds = RSSFeed.objects.filter(user=user)
    for rss_feed in rss_feeds:
        refresh_mirrored_rss_feed(user, rss_feed)

    return redirect('profile')

def refresh_mirrored_rss_feed(user, rss_feed):
    if rss_feed:
        feed = feedparser.parse(rss_feed.link)

        for entry in reversed(feed.entries):
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')

            post_timestamp = parse_timestamp(entry)
            if post_timestamp is None:
                post_timestamp = datetime.now()

            if not Post.objects.filter(user=user, title=title, body=body, is_rss_feed_post=True).exists():
                Post.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    is_rss_feed_post=True,
                    timestamp=post_timestamp
                )
    return

def delete_rss_feed(request, rss_feed_id):
    if request.method == 'POST':
        rss_feed = RSSFeed.objects.get(id=rss_feed_id)
        rss_feed.delete()
        return redirect('rss')
    else:
        return HttpResponseBadRequest("Invalid request method")

def landing(request):
    return render(request, 'Linkfeed/landingpage.html')

def search_users(request):
    if request.method == 'GET':
        profile = Profile.objects.get(user=request.user)
        return render(request, 'Linkfeed/search.html', {'profile': profile})
    elif request.method == 'POST':
        profile = Profile.objects.get(user=request.user)
        query = request.POST.get('query')
        profiles = Profile.objects.filter(
            Q(user__username__icontains=query) | 
            Q(display_name__icontains=query) | 
            Q(domain__icontains=query)
        ).annotate(
            followers_count=Count('follower')
        ).order_by(
            '-followers_count'
        ).exclude(
            user__is_superuser=True
        )
        return render(request, 'Linkfeed/search.html', {'profiles': profiles, 'profile': profile, 'query': query})