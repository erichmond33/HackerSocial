from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse,HttpResponseForbidden, JsonResponse, HttpResponseBadRequest

from django.urls import reverse

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import User, Post, Profile, Comment, PostLike

from django.http import Http404



@login_required
def index(request):
    # Retrieve the authentication token from the session
    auth_token = request.session.get('auth_token', None)
    return render(request, "Linkfeed/index.html", {"auth_token": auth_token})


def current_user_profile(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    else:
        posts = Post.objects.filter(user=request.user)
        profile = get_object_or_404(Profile, user=request.user)
        return render(request, "Linkfeed/profile.html", {"posts": posts, "profile": profile})

def profile(request, username):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    else:
        profile_user = get_object_or_404(User, username=username)
        # Check if the requested profile is the profile of the logged-in user
        if profile_user == request.user:
            return redirect('current_user_profile')
        else:
            posts = Post.objects.filter(user=profile_user)
            profile = get_object_or_404(Profile, user=profile_user)
            return render(request, "Linkfeed/other_profile.html", {"posts": posts, "profile": profile})


    
def feed(request):
    if request.user.is_authenticated:
        try:
            # Retrieve the profile associated with the current user
            profile = Profile.objects.get(user=request.user)
            # Retrieve the IDs of Linkfeed that the current user is following
            following_ids = profile.following.values_list('id', flat=True)
            # Retrieve posts from the Linkfeed that the current user is following
            posts = Post.objects.filter(user__id__in=following_ids)
            return render(request, 'Linkfeed/feed.html', {'posts': posts})
        except Profile.DoesNotExist:
            # Handle the case where the user doesn't have a profile
            return redirect('login')  # Redirect to login page or handle as appropriate
    else:
        return redirect('login')





def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Pass the authentication token to the session
            request.session['auth_token'] = request.session.session_key
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "Linkfeed/login.html", {
                "message": "Invalid credentials."
            })

    return render(request, "Linkfeed/login.html")





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

def delete_comment(request, comment_id):
    if request.method == "DELETE":
        comment = get_object_or_404(Comment, id=comment_id)
        # Check if the user is authenticated and is the owner of the comment
        if comment.user == request.user:
            comment.delete()
            # Return a JSON response indicating success
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('profile')))
        else:
            # Return a forbidden response if the user is not the owner of the comment
            return HttpResponseForbidden("You are not authorized to delete this comment.")



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
    post = get_object_or_404(Post, id=request.POST.get('post_id'))
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return HttpResponseRedirect(reverse('post', args=[str(pk)]))


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







