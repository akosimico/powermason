from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.views import redirect_to_login

def verified_email_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.emailaddress_set.filter(verified=True).exists():
                return view_func(request, *args, **kwargs)
            else:
                return redirect('email_verification_required')
        else:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
    return _wrapped_view


def role_required(*allowed_roles):
    """
    Example:
    @role_required('PM', 'OP')  # Only Project Manager or Operations Manager
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            # Superuser bypasses role checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check if user has profile and allowed role
            if hasattr(request.user, 'userprofile'):
                if request.user.userprofile.role in allowed_roles:
                    return view_func(request, *args, **kwargs)

            return redirect('unauthorized')  # Redirect if not authorized

        return _wrapped_view
    return decorator