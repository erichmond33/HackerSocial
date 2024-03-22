from django.urls import path
from django.contrib import admin
from Linkfeed import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("post", views.post, name="post"),
    path("following", views.following, name="following"),
    path('admin/', admin.site.urls),    
    # API Routes
    path("send", views.send, name="send"),
    path("feed", views.view_feed, name="view_feed"),
    path("profile/<str:username>", views.profile, name="profile"),
    path("profile_data/<str:username>", views.profile_data, name="profile_data"),
    path("follow", views.follow, name="follow"),
    path("edit/<int:post_id>", views.edit, name="edit"),
    path("like/<int:post_id>", views.like, name="like"),
]