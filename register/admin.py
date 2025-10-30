from django.contrib import admin
from .models import UserProfile

# Register your models here.
@admin.register(UserProfile)
class UserProfile(admin.ModelAdmin):
    list_display = ('user', 'phone', 'pickup', 'is_staff')
    search_fields = ('user', 'phone', 'pickup')
    list_filter = ('pickup',)