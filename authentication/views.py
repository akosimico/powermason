# Standard library
import json
from decimal import Decimal
from datetime import date

# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.signing import BadSignature, SignatureExpired
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.core.serializers.json import DjangoJSONEncoder

# Authentication utils & decorators
from authentication.utils.tokens import parse_dashboard_token, make_dashboard_token, _resolve_profile_from_token
from authentication.utils.decorators import verified_email_required, role_required

# Local app imports
from .models import UserProfile
from .forms import StyledPasswordChangeForm
from scheduling.models import ProgressUpdate
from scheduling.forms import ProjectTask
from project_profiling.models import ProjectProfile, ProjectBudget, ProjectCost, FundAllocation

User = get_user_model()
# --- Utility function to calculate project progress dynamically ---

def verify_user_token(request, token, role):
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
    except SignatureExpired:
        messages.error(request, "Your session token has expired.")
        return redirect("unauthorized")
    except BadSignature:
        messages.error(request, "Invalid token. Access denied.")
        return redirect("unauthorized")

    if role != token_role:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("unauthorized")

    try:
        profile_from_token = UserProfile.objects.get(user__id=user_uuid)
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found for this token.")
        return redirect("unauthorized")

    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    return profile_from_token  # return verified profile

def calculate_project_progress(project_id):
    tasks = ProjectTask.objects.filter(project_id=project_id)
    total_weight = sum(t.weight for t in tasks) or Decimal("1")
    progress = Decimal("0")

    for t in tasks:
        latest_update = t.updates.filter(status='A').order_by('-reviewed_at').first()
        if latest_update:
            progress += (t.weight / total_weight) * Decimal(latest_update.progress_percent)

    return round(progress, 2)


# --- Redirect logged-in user to their dashboard with token ---
@login_required
def redirect_to_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    token = make_dashboard_token(profile)
    role = profile.role
    
    request.session['dashboard_token'] = token
    request.session.save()
    
    return redirect('dashboard_signed_with_role', token=token, role=role)


@login_required
@verified_email_required
@role_required('EG', 'OM', 'PM')
def dashboard_signed_with_role(request, token, role):
    
    profile = verify_user_token(request, token, role) 

    # --- Fetch projects ---
    if profile.role == "PM":
        projects = ProjectProfile.objects.filter(project_manager=profile)
    else:
        projects = ProjectProfile.objects.all()

    # --- Status counts ---
    status_counts = {
        "planned": projects.filter(status="PL").count(),
        "ongoing": projects.filter(status="OG").count(),
        "completed": projects.filter(status="CP").count(),
        "cancelled": projects.filter(status="CN").count(),
    }

    # --- Prepare project data ---
    project_data = []
    projects_data_for_json = []
    overall_budget_summary = {"planned": Decimal("0.00"), "allocated": Decimal("0.00"), "spent": Decimal("0.00")}

    for project in projects:
        # --- Tasks ---
        tasks = ProjectTask.objects.filter(project=project).order_by("start_date")
        task_progress = [(task.task_name, round(task.progress, 2), task.weight) for task in tasks]

        total_weight = sum(task.weight for task in tasks) or Decimal("1")
        total_progress = sum((task.progress * task.weight) for task in tasks) / total_weight

        # Planned progress calculation
        planned_progress = 0
        if project.start_date and project.target_completion_date:
            total_days = max((project.target_completion_date - project.start_date).days, 1)
            elapsed_days = max((date.today() - project.start_date).days, 0)
            planned_progress = min(100, (elapsed_days / total_days) * 100)

         # --- Budget aggregation ---
        budgets = ProjectBudget.objects.filter(project=project)
        category_summary = []
        project_budget_total = {"planned": Decimal("0.00"), "allocated": Decimal("0.00"), "spent": Decimal("0.00")}

        for budget in budgets:
            planned = budget.planned_amount or Decimal("0.00")

            allocated = FundAllocation.objects.filter(
                project_budget__project=project,
                project_budget__category=budget.category
            ).aggregate(
                total=Coalesce(Sum('amount'), Decimal("0.00"))
            )['total']

            spent = ProjectCost.objects.filter(
                project=project,
                category=budget.category
            ).aggregate(
                total=Coalesce(Sum('amount'), Decimal("0.00"))
            )['total']

            category_summary.append({
                "category": budget.get_category_display(),
                "planned": planned,
                "allocated": allocated,
                "spent": spent,
            })

            project_budget_total["planned"] += planned
            project_budget_total["allocated"] += allocated
            project_budget_total["spent"] += spent

        # --- Add to overall summary ---
        overall_budget_summary["planned"] += project_budget_total["planned"]
        overall_budget_summary["allocated"] += project_budget_total["allocated"]
        overall_budget_summary["spent"] += project_budget_total["spent"]
        print(f"   🔹 Project budget total: {project_budget_total}")  # Debug

        # --- Append project data ---
        project_data.append({
            "project_name": project.project_name,
            "project_status": project.status,
            "task_progress": task_progress,
            "total_progress": round(total_progress, 2),
            "planned_progress": round(planned_progress, 2),
            "budget_summary": category_summary,
            "budget_total": project_budget_total,
        })

        projects_data_for_json.append({
            "id": project.id,
            "name": project.project_name,
            "status": project.status,
            "actual_progress": round(total_progress, 2),
            "planned_progress": round(planned_progress, 2),
            "budget_summary": category_summary,
            "budget_total": project_budget_total,
            "tasks": [
                {
                    "title": task.task_name,
                    "start": task.start_date.isoformat() if task.start_date else None,
                    "end": task.end_date.isoformat() if task.end_date else None,
                    "progress": round(task.progress, 2),
                } for task in tasks
            ],
        })

    projects_json = json.dumps(projects_data_for_json, cls=DjangoJSONEncoder)

    context = {
        "profile": profile,
        "projects": project_data,
        "projects_json": projects_json,
        "status_counts": status_counts,
        "overall_budget_summary": overall_budget_summary,
        "token": token,
        "role": role,
    }

    return render(request, "dashboard.html", context)

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
@login_required
@verified_email_required
def settings(request):
    return render(request, 'account/settings.html', status=403)

def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)


@login_required
@role_required('EG', 'OM')
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