from django.contrib import admin
from .models import Profile
# Register your models here.

#Displays the Profile in admin dashboard
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "account_type", "phone_number")