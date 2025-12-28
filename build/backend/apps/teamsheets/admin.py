from django.contrib import admin
from .models import *

class TeamsheetPlayerInline(admin.TabularInline):
    model = TeamsheetPlayer
    extra = 1

@admin.register(Teamsheet)
class TeamsheetAdmin(admin.ModelAdmin):
    list_display = ('formation', 'title')
    search_fields = ('title', 'formation')

@admin.register(TeamsheetPlayer)
class TeamsheetPlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'position')
    list_filter = ('position', 'name')
    search_fields = ('name', 'number')

