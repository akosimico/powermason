from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# Inline for UserProfile inside User admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

# Extend User admin to include the profile inline
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Unregister default User admin and register the new one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Keep a separate UserProfile admin (list view with search)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'full_name', 'user__email')
