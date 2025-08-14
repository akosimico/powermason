# Standard library
import json

# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q


# Local app imports
from authentication.decorators import verified_email_required, role_required
from .models import UserProfile
from .forms import StyledPasswordChangeForm
from authentication.decorators import verified_email_required

User = get_user_model()

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'account/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('account_change_password')

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, "Your password has been changed successfully!")
        return super().form_valid(form)

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def login(request):
    return render(request, 'login.html')

@login_required
@verified_email_required
def profile(request):
    return render(request, 'account/profile.html')

@login_required
def email_verification_required(request):
    if request.user.emailaddress_set.filter(verified=True).exists():
        return redirect('profile')
    return render(request, 'account/verified_email_required.html')

def unauthorized(request):
    return render(request, 'account/unauthorized.html', status=403)

def settings(request):
    return render(request, 'account/settings.html', status=403)


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)


@login_required
@role_required('EG', 'OM')
# @superuser_required
def manage_user_profiles(request):
    search_query = request.GET.get("q", "")
    role_filter = request.GET.get("role", "")
    profiles = UserProfile.objects.select_related('user')

    # Filter table by search or role
    if search_query:
        profiles = profiles.filter(
            Q(user__username__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    if role_filter:
        profiles = profiles.filter(role=role_filter)

    if request.method == "POST":
        profile_id = request.POST.get("profile_id")
        role = request.POST.get("role")
        full_name = request.POST.get("full_name")

        # Validate inputs
        if not profile_id or not role:
            messages.error(request, "Please select a user and role.")
            return redirect("manage_user_profiles")

        profile = get_object_or_404(UserProfile, id=profile_id)
        profile.role = role
        profile.full_name = full_name or profile.full_name
        profile.save()

        messages.success(request, f"{profile.user.username}'s profile updated.")
        return redirect("manage_user_profiles")

    return render(request, "users/manage_user_profiles.html", {
        "profiles": profiles,
        "ROLE_CHOICES": UserProfile.ROLE_CHOICES,
        "ROLE_CHOICES_JSON": json.dumps(UserProfile.ROLE_CHOICES),
        "search_query": search_query,
        "role_filter": role_filter,
    })
    
@login_required
@superuser_required
def search_users(request):
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')
    
    users = UserProfile.objects.select_related('user')
    
    if q:
        users = users.filter(
            Q(user__username__icontains=q) |
            Q(full_name__icontains=q) |
            Q(user__email__icontains=q)
        )
    if role:
        users = users.filter(role=role)

    users = users[:20]  # limit for performance

    results = []
    for u in users:
        if not u.user:  # skip broken profiles
            continue
        results.append({
            'id': u.id,
            'username': u.user.username,
            'full_name': u.full_name or '',
            'email': u.user.email or '',
            'role': u.role or '',
        })

    return JsonResponse(results, safe=False)