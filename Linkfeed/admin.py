from django.contrib import admin
from django.contrib.auth.admin import UserAdmin


from .models import User, Post, Profile, Comment, PostLike, RSSFeed, ImportedRSSFeed, UserCSS, AllowedDomain




# Register your models here.


# admin.site.register(User)


class UserAdmin(UserAdmin):
    pass

admin.site.register(User, UserAdmin)
admin.site.register(Post)
admin.site.register(Profile)
admin.site.register(Comment)
admin.site.register(PostLike)
admin.site.register(RSSFeed)
admin.site.register(ImportedRSSFeed)

admin.site.register(UserCSS)

admin.site.register(AllowedDomain)


