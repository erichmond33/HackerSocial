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
from datetime import datetime
import pytz
import time 
from Linkfeed.decorators import prevent_iframe_embedding
from django.views.decorators.http import require_GET

from .decorators import CSPDecorator  # Import your decorator


def index(request):
    if request.user.is_authenticated:
        return render(request, "Linkfeed/index.html")
    else:
        return redirect('login')
    
def landing(request):
    return render(request, "Linkfeed/index.html")

@CSPDecorator
def current_user_profile(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    else:
        try:
            posts = Post.objects.filter(user=request.user).order_by('-timestamp')
            profile = get_object_or_404(Profile, user=request.user)
            # Check if the current user has liked each post
            for post in posts:
                post.liked = post.likes.filter(id=request.user.id).exists()

            return render(request, "Linkfeed/profile.html", {"posts": posts, "profile": profile})
        except Http404:
            # Handle the case where RSSFeed object does not exist for the user
            return render(request, "Linkfeed/profile.html", {"posts": posts, "profile": profile})

from django.db.models import Count

@CSPDecorator
def profile(request, username):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    else:
        profile_user = get_object_or_404(User, username=username)
        # Check if the requested profile is the profile of the logged-in user
        if profile_user == request.user:
            return redirect('current_user_profile')
        else:
            posts = Post.objects.filter(user=profile_user).annotate(total_comments=Count('comments')).order_by('-timestamp')
            profile = get_object_or_404(Profile, user=profile_user)
            # Check if the current user has liked each post
            for post in posts:
                post.liked = post.likes.filter(id=request.user.id).exists()
                
            return render(request, "Linkfeed/other_profile.html", {"posts": posts, "profile": profile})

@CSPDecorator
@login_required
def current_user_feed(request):
    try:
        # Retrieve the profile associated with the current user
        profile = Profile.objects.get(user=request.user)
        # Retrieve the IDs of Linkfeed that the current user is following
        following_ids = profile.following.values_list('id', flat=True)
        # Retrieve posts from the Linkfeed that the current user is following
        posts = Post.objects.filter(
            Q(user=request.user) | (Q(user__id__in=following_ids) & ~Q(is_imported_rss_feed_post=True))
        ).annotate(total_comments=Count('comments')).order_by('-timestamp')

        imported_rss_feeds = ImportedRSSFeed.objects.filter(user=request.user)

        # Check if the current user has liked each post
        for post in posts:
            post.liked = post.likes.filter(id=request.user.id).exists()

        return render(request, 'Linkfeed/feed.html', {'posts': posts, 'imported_feeds': imported_rss_feeds, 'profile': profile})
    except Profile.DoesNotExist:
        # Handle the case where the user doesn't have a profile
        return redirect('login')  # Redirect to login page or handle as appropriate
    
    
@CSPDecorator     
def feed(request, username):
    # Retrieve the user object based on the username
    user = User.objects.get(username=username)
    profile = Profile.objects.get(user=user)

    # Retrieve the IDs of Linkfeed that the user is following
    following_ids = user.profile.following.values_list('id', flat=True)

    # Retrieve posts from the Linkfeed that the user is following and not imported RSS feed posts
    posts = Post.objects.filter(
        Q(user__id__in=following_ids) & ~Q(is_imported_rss_feed_post=True)
    ).annotate(total_comments=Count('comments')).order_by('-timestamp')

    imported_rss_feeds = ImportedRSSFeed.objects.filter(user=user)

    # Check if the user has liked each post
    for post in posts:
        post.liked = post.likes.filter(id=user.id).exists()

    context = {
        'posts': posts,
        'imported_feeds': imported_rss_feeds,
        'user': user,
        'profile': profile,  # Add profile to the context
    }
    # Check if the current user has liked each post
    for post in posts:
        post.liked = post.likes.filter(id=request.user.id).exists()
    return render(request, 'Linkfeed/other_feed.html', context)




@prevent_iframe_embedding
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


@prevent_iframe_embedding
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


@prevent_iframe_embedding        
def logout_view(request):
    logout(request)
    return render(request, "Linkfeed/login.html", {
        "message": "Logged out."
    })


@CSPDecorator
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
        
@CSPDecorator
def add_comment(request, post_id):
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        parent_comment_id = request.POST.get("parent_comment_id")  # Get the ID of the parent comment if it's a reply
        parent_comment = None
        if parent_comment_id:
            parent_comment = get_object_or_404(Comment, id=parent_comment_id)
        comment_body = request.POST.get("comment_body")
        # Create a new comment object and save it to the database
        comment = Comment.objects.create(user=request.user, post=post, body=comment_body, parent_comment=parent_comment)
        # Redirect to the post detail page after adding the comment
        return redirect("post", post_id=post_id)
    # Handle other HTTP methods if necessary


from django.shortcuts import redirect
from django.contrib import messages
@CSPDecorator
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




@CSPDecorator
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
@CSPDecorator
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

@CSPDecorator
@login_required
def edit_profile(request):
    if request.method == "POST":
        # Get the current user's profile instance
        profile = get_object_or_404(Profile, user=request.user)
        
        # Retrieve the new link from the POST data
        new_link = request.POST.get('link')
        
        # Update the profile link with the new value
        profile.link = new_link
        
        # Save the updated profile
        profile.save()
        
        # Redirect to the profile page after editing
        return redirect('profile')
    else:
        # Handle GET request (display edit profile form)
        return HttpResponseForbidden("You are not authorized to edit this profile.")
@CSPDecorator
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
    

@CSPDecorator
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


@CSPDecorator
@login_required
def followers_view(request, username):
    # Get the profile of the user whose followers you want to see
    user_profile = get_object_or_404(Profile, user__username=username)
    # Get the followers of the user
    followers = user_profile.follower.all()
    return render(request, 'Linkfeed/followers.html', {'followers': followers})

@CSPDecorator
@login_required
def following_view(request, username):
    # Get the profile of the user whose following you want to see
    user_profile = get_object_or_404(Profile, user__username=username)
    # Get the Linkfeed followed by the user
    following = user_profile.following.all()
    return render(request, 'Linkfeed/following.html', {'following': following})

@CSPDecorator
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
@CSPDecorator    
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





import datetime
import dateutil.parser 

def parse_timestamp(timestamp_str):
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',  # Original format
        '%a, %d %b %Y %H:%M:%S %Z'  # pubDate format
    ]
    for field_name in ['published', 'pubDate', 'dc:date', 'atom:published', 'dc:created']:
        timestamp = timestamp_str.get(field_name)
        if timestamp:
            for fmt in formats:
                try:
                    if fmt == '%Y-%m-%dT%H:%M:%S%z':
                        return datetime.datetime.strptime(timestamp, fmt)
                    else:
                        return dateutil.parser.parse(timestamp) 
                except ValueError:
                    continue
    return None

@CSPDecorator
def mirror_rss_feed(request):
    form = RSSFeedForm(request.POST or None)
    user = request.user

    if request.method == 'POST':
        if form.is_valid():
            rss_feed_link = form.cleaned_data['link']
            existing_feed = RSSFeed.objects.filter(user=user).first()
            if existing_feed:
                Post.objects.filter(user=user, is_rss_feed_post=True).delete()
                existing_feed.link = rss_feed_link
                existing_feed.save()
            else:
                RSSFeed.objects.create(user=user, link=rss_feed_link)
            return HttpResponseRedirect(request.path_info)

    rss_feed = RSSFeed.objects.filter(user=request.user).first()
    if rss_feed:
        existing_titles = set(Post.objects.filter(user=user, is_rss_feed_post=True).values_list('title', flat=True))
        Post.objects.filter(user=user, is_rss_feed_post=True).delete()

        feed = feedparser.parse(rss_feed.link)
        entries = feed.entries
        
        for entry in reversed(entries):
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')  # You can change this to get other fields like summary
            # Extract timestamp from the entry
            timestamp_str = {
                'published': entry.get('published'),
                'pubDate': entry.get('pubDate'),
                'dc:date': entry.get('dc:date'),
                'atom:published': entry.get('atom:published'),
                'dc:created': entry.get('dc:created')
            }
            post_timestamp = parse_timestamp(timestamp_str)
            if post_timestamp is None:
                post_timestamp = datetime.datetime.now()
            
            # Check if a post with the same title and timestamp already exists
            if title not in existing_titles or not Post.objects.filter(user=user, title=title, timestamp=post_timestamp).exists():
                new_post = Post.objects.create(user=user, title=title, body=body, is_rss_feed_post=True, timestamp=post_timestamp)
                existing_titles.add(title)  # Add title to existing titles set
    else:
        entries = []  # Handle case where RSS feed is not available

    return redirect('profile')



@CSPDecorator
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
                    published_time = entry.get('published')
                    updated_time = entry.get('updated')
                    timestamp_str = {'published': published_time, 'updated': updated_time}
                    post_timestamp = parse_timestamp(timestamp_str)
                    if post_timestamp is None:
                        post_timestamp = datetime.datetime.now()  # Use current time if timestamp not found
                    # Check if a post with the same title already exists
                    if not Post.objects.filter(user=user, title=title).exists():
                        new_post = Post.objects.create(
                            user=user,
                            title=title,
                            body=body,
                            is_imported_rss_feed_post=True,
                            imported_rss_feed=new_imported_feed,
                            timestamp=post_timestamp
                        )
            # refresh_imported_rss_feed(request)
            return HttpResponseRedirect(request.path_info)

    user_imported_rss_feeds = ImportedRSSFeed.objects.filter(user=user)
    for imported_feed in user_imported_rss_feeds:
        feed = feedparser.parse(imported_feed.link)
        entries = feed.entries
        for entry in reversed(entries):
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')
            published_time = entry.get('published')
            updated_time = entry.get('updated')
            timestamp_str = {'published': published_time, 'updated': updated_time}
            post_timestamp = parse_timestamp(timestamp_str)
            if post_timestamp is None:
                post_timestamp = datetime.datetime.now()  # Use current time if timestamp not found
            # Check if a post with the same title already exists
            if not Post.objects.filter(user=user, title=title).exists():
                new_post = Post.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    is_imported_rss_feed_post=True,
                    imported_rss_feed=imported_feed,
                    timestamp=post_timestamp
                )
    # refresh_imported_rss_feed(request)
    return redirect('current_user_feed')





@CSPDecorator
def delete_imported_feed(request, feed_id):
    imported_rss_feed = get_object_or_404(ImportedRSSFeed, id=feed_id, user=request.user)
    # Delete posts associated with the imported RSS feed
    Post.objects.filter(user=request.user, imported_rss_feed=imported_rss_feed).delete()
    # Delete the imported RSS feed itself
    imported_rss_feed.delete()
    return redirect('current_user_feed')

@CSPDecorator
def refresh_mirrored_rss_feed(request):
    user = request.user
    rss_feed = RSSFeed.objects.filter(user=user).first()

    if rss_feed:
        feed = feedparser.parse(rss_feed.link)

        for entry in reversed(feed.entries):  # Use reversed to get newest posts first
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')
            post_timestamp = parse_timestamp(entry)  # Extract timestamp

            if post_timestamp is None:
                post_timestamp = datetime.datetime.now()  # Use current time as fallback

            if not Post.objects.filter(user=user, title=title, body=body, is_rss_feed_post=True).exists():
                Post.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    is_rss_feed_post=True,
                    timestamp=post_timestamp  # Use the extracted timestamp
                )

    return redirect('profile')

@CSPDecorator
def refresh_imported_rss_feed(request):
    user = request.user
    imported_rss_feeds = ImportedRSSFeed.objects.filter(user=user)

    for imported_feed in imported_rss_feeds:
        feed = feedparser.parse(imported_feed.link)

        for entry in reversed(feed.entries):  # Use reversed to get newest posts first
            title = entry.get('title', 'No Title')
            body = entry.get('link', 'No Link')
            post_timestamp = parse_timestamp(entry)  # Extract timestamp

            if post_timestamp is None:
                post_timestamp = datetime.datetime.now()  # Use current time as fallback

            if not Post.objects.filter(user=user, title=title, body=body, is_imported_rss_feed_post=True, imported_rss_feed=imported_feed).exists():
                Post.objects.create(
                    user=user,
                    title=title,
                    body=body,
                    is_imported_rss_feed_post=True,
                    imported_rss_feed=imported_feed,
                    timestamp=post_timestamp  # Use the extracted timestamp
                )

    return redirect('current_user_feed')







from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse

import datetime
@CSPDecorator
def repost_view(request, post_id):
    original_post = get_object_or_404(Post, pk=post_id)

    try:
        # Attempt to retrieve the retweeted post for the current user
        retweeted_post = Post.objects.get(user=request.user, is_rss_feed_post=False, is_imported_rss_feed_post=False, imported_rss_feed=None, title=f"Repost: {original_post.title}")
        
        # If the retweeted post exists, delete it and decrement the repost count
        original_post.repost_count -= 1
        original_post.save()
        retweeted_post.delete()
    except Post.DoesNotExist:
        # If the retweeted post does not exist, create it and increment the repost count
        timestamp = datetime.datetime.now()  # Set the current timestamp
        Post.objects.create(
            user=request.user,
            title=f"Repost: {original_post.title}",
            body=original_post.body,
            is_rss_feed_post=False,
            is_imported_rss_feed_post=False,
            imported_rss_feed=None,
            timestamp=timestamp  # Set the timestamp
        )
        original_post.repost_count += 1
        original_post.save()

    # Redirect back to the previous page
    return redirect(request.META.get('HTTP_REFERER', reverse('current_user_profile')))
