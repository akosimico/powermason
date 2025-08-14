from django.templatetags.static import static

def avatar_url(request):
    """Return the best avatar URL for the authenticated user."""
    if not request.user.is_authenticated:
        return {'avatar_url': static('img/default-avatar.jpg')}

    social = request.user.socialaccount_set.first()
    if social and social.get_avatar_url():
        return {'avatar_url': social.get_avatar_url()}

    # Fallback to default image
    return {'avatar_url': static('img/default-avatar.jpg')}
