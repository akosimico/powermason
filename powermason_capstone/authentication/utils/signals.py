from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from authentication.models import UserProfile

User = get_user_model()
# --- Auto-create a single superuser after migration ---
@receiver(post_migrate)
def create_superuser(sender, **kwargs):
    if User.objects.filter(is_superuser=True).count() < 1:
        username = 'admin'
        User.objects.create_superuser(
            username=username,
            email=f'{username}@example.com',
            password='admin123'
        )
        print(f"✅ Superuser '{username}' created automatically.")
        
# --- Auto-create profile for every new user ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            full_name=instance.get_full_name() or instance.username
        )
