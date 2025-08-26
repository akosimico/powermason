from django.templatetags.static import static
from scheduling.models import ProgressUpdate
from authentication.models import UserProfile
from authentication.utils.tokens import make_dashboard_token  # import your token function

def user_context(request):
    """
    Provides avatar, pending updates, role, and dashboard token globally.
    """
    user = request.user
    context = {
        'avatar_url': static('img/default-avatar.jpg'),
        'pending_count': 0,
        'role': None,
        'dashboard_token': None,
    }

    if user.is_authenticated:
        # Avatar
        social = user.socialaccount_set.first()
        context['avatar_url'] = social.get_avatar_url() if social else context['avatar_url']

        # Role
        role = getattr(user, 'role', None)
        context['role'] = role

        # Pending count (OM, EG, or superuser)
        if role in ['OM', 'EG'] or user.is_superuser:
            context['pending_count'] = ProgressUpdate.objects.filter(status='P').count()

        # Generate dashboard token for authenticated users
        try:
            profile = UserProfile.objects.get(user=user)
            context['dashboard_token'] = make_dashboard_token(profile)
        except UserProfile.DoesNotExist:
            context['dashboard_token'] = None

    return context
