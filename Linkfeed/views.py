from django.shortcuts import render
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.http.response import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators import csrf
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from .models import User, Post, Profile

def index(request):

    # Authenticated users view their inbox
    if request.user.is_authenticated:
        return render(request, "network/index.html")


    # Everyone else is prompted to sign in
    else:
        return HttpResponseRedirect(reverse("login"))


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        profile = Profile()
        profile.user = user
        profile.save()
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")

def post(request):
    return render(request, "network/post.html")

@csrf_exempt
@login_required
def send(request):

    # Composing a new email must be via POST
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)

    # Get the data
    data = json.loads(request.body)
    body = data.get("post", "")

    user_post = Post(user=request.user, body=body)
    user_post.save()

    return JsonResponse({"message": "Posted Loverducker"}, status=201)

@login_required
def view_feed(request):

    #Get the posts
    feed = Post.objects.all()

    # Return posts in chronologial order
    feed = feed.order_by("-timestamp").all()

    return JsonResponse([x.serialize() for x in feed], safe=False)

@login_required
def profile_data(request, username):

    try:
        user = User.objects.get(username = username)
        profile = Profile.objects.get(user = user)

        if request.user in profile.follower.all():
            action = "Unfollow"
        else:
            action = "Follow"

        return JsonResponse({'status': 201, "follower_count" : profile.follower.count(), "following_count" : profile.following.count(), "action" : action}, status=201)
    except:
        return JsonResponse({"error": f"User not found.{request.user}"}, status=404)

@login_required
def following(request):

    following = Profile.objects.get(user=request.user).following.all()
    posts = Post.objects.filter(user__in=following).order_by('-timestamp')
    paginator = Paginator(posts, 10)
    if request.GET.get("page") != None:
        try:
            posts = paginator.page(request.GET.get("page"))
        except:
            posts = paginator.page(1)
    else:
        posts = paginator.page(1)
    return render(request, 'network/following.html', {'posts': posts})

@login_required
def profile(request, username):
 
    # Query for requested email
    try:
        user_feed = Post.objects.filter(user=username)
    except Post.DoesNotExist:
        return JsonResponse({"error": f"User not found.{request.user}"}, status=404)

    # Return email contents
    if request.method == "GET":
        return JsonResponse([y.serialize() for y in user_feed], safe=False)
    
    # Email must be via GET or PUT
    else:
        return JsonResponse({
            "error": "GET or PUT request required."
        }, status=400)

    # Update whether email is read or should be archived
    '''elif request.method == "PUT":
        data = json.loads(request.body)
        if data.get("read") is not None:
            email.read = data["read"]
        if data.get("archived") is not None:
            email.archived = data["archived"]
        email.save()
        return HttpResponse(status=204)'''

@login_required
@csrf_exempt
def follow(request):

    if (request.method == "POST"):
        user = request.POST.get("user")
        action = request.POST.get("action")

        if action == "Follow":
            try:
                user = User.objects.get(username=user)
                profile = Profile.objects.get(user=request.user)
                profile.following.add(user)
                profile.save()

                profile = Profile.objects.get(user=user)
                profile.follower.add(request.user)
                profile.save

                return JsonResponse({'status': 201, 'action' : "Unfollow", "follower_count" : profile.follower.count()}, status=201)
            except:
                return JsonResponse({}, status=404)

        else:
            try:
                # add user to current user's following list
                user = User.objects.get(username=user)
                profile = Profile.objects.get(user=request.user)
                profile.following.remove(user)
                profile.save()

                # add current user to  user's follower list
                profile = Profile.objects.get(user=user)
                profile.follower.remove(request.user)
                profile.save()
                return JsonResponse({'status': 201, 'action': "Follow", "follower_count": profile.follower.count()}, status=201)
            except:
                return JsonResponse({}, status=404)

    return JsonResponse({}, status=400)

@login_required
@csrf_exempt
def edit(request, post_id):

    # Query for requested email
    try:
        post = Post.objects.get(id=post_id)
        
        data = json.loads(request.body)

        post.body = data["content"]
        post.save()
        return JsonResponse({"post" : f"{post.body}"}, status=201)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Email not found."}, status=404)

@login_required
@csrf_exempt
def like(request, post_id):


    #Add or take away a like
    try:
        post = Post.objects.get(id=post_id)
        print(f"{post.likes} <-----")
        if post.likes == "":
            post.likes = "0"
        print(f"{post.likes} <-----")

        post.likes = str(int(post.likes) + 1)
        print(f"{post.likes} <-----")

        post.save()
        return JsonResponse({"likes": f"{post.likes}"}, status=201)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post aint exsist"}, status=404)