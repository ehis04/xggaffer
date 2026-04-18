from django.contrib import admin
from .models import Post, Comment, Like, HashTag, PostTag, Mention, Notification, Block, UserInterestProfile, UserAuthorInterest, UserHashtagInterest

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(HashTag)
admin.site.register(PostTag)
admin.site.register(Mention)
admin.site.register(Notification)
admin.site.register(Block)
admin.site.register(UserInterestProfile)
admin.site.register(UserAuthorInterest)
admin.site.register(UserHashtagInterest)