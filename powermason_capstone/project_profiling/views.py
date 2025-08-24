from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, SignatureExpired
from authentication.utils.tokens import parse_dashboard_token, make_dashboard_token
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
from django.db.models import Q
from decimal import Decimal

from scheduling.models import ProjectTask
from authentication.models import UserProfile
from authentication.utils.decorators import verified_email_required, role_required
from .forms import ProjectProfileForm, GeneralContractorForm, DirectClientForm
from .models import ProjectProfile, ProjectFile
from authentication.views import _resolve_profile_from_token

def project_dashboard(request, project_id):
    project = get_object_or_404(ProjectProfile, id=project_id)

    # Get all tasks for this project
    tasks = ProjectTask.objects.filter(project=project)

    # Progress list for template
    task_progress = [(task, task.progress) for task in tasks]

    # Weighted total progress (use Decimal to avoid type errors)
    total_weight = sum(task.weight for task in tasks) or Decimal("1")
    total_progress = sum((task.progress * task.weight) for task in tasks) / total_weight

    context = {
        "project": project,
        "task_progress": [(task, round(progress, 2)) for task, progress in task_progress],
        "total_progress": round(total_progress, 2),
    }
    return render(request, "progress/dashboard.html", context)
    
@login_required
def project_list_default(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    token = make_dashboard_token(profile)
    role = profile.role

    # Redirect to /projects/<token>/list/<role>/
    return redirect('project_list', token=token, role=role)

def search_project_managers(request):
    query = request.GET.get('q', '')
    project_managers = UserProfile.objects.filter(role='PM').select_related("user")

    if query:
        project_managers = project_managers.filter(
            Q(full_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )

    data = [
        {
            "id": u.id,  # 🔥 use User ID, not UserProfile ID
            "username": u.user.username,
            "full_name": u.full_name,
            "email": u.user.email,
        }
        for u in project_managers
    ]
    return JsonResponse(data, safe=False)

@login_required
@verified_email_required
@role_required('PM', 'OM', 'EG')
def project_list_signed_with_role(request, token, role):
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
    except SignatureExpired:
         return redirect("unauthorized")
    except BadSignature:
         return redirect("unauthorized")

    if role != token_role:
         return redirect("unauthorized")

    try:
        profile_from_token = UserProfile.objects.get(user__id=user_uuid)
    except UserProfile.DoesNotExist:
         return redirect("unauthorized")

    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    # Handle file upload
    if request.method == "POST" and "project_id" in request.POST:
        project_id = request.POST.get("project_id")
        project = get_object_or_404(ProjectProfile, id=project_id)

        # 🔒 Ensure user has permission to upload to this project
        if role == "PM" and project.project_manager != profile_from_token:
            return HttpResponse("Unauthorized upload")
        if role == "OM" and not (project.created_by == profile_from_token or project.assigned_to == profile_from_token):
            return HttpResponse("Unauthorized upload")

        files = request.FILES.getlist("file")
        for f in files:
            ProjectFile.objects.create(project=project, file=f)

        return redirect("project_list_signed_with_role", token=token, role=role)

    # Fetch projects
    if profile_from_token.role == 'EG':
        projects = ProjectProfile.objects.all()
    elif profile_from_token.role == 'PM':
        projects = ProjectProfile.objects.filter(project_manager=profile_from_token)
    else:
        projects = ProjectProfile.objects.filter(
            Q(created_by=profile_from_token) | Q(assigned_to=profile_from_token)
        ).distinct()

    context = {
        'dashboard_token': token,
        'user_uuid': user_uuid,
        'role': role,
        'projects': projects,
    }
    return render(request, 'project_profiling/project_list.html', context)


@verified_email_required
@role_required('PM')
def project_view(request, token, role, project_type, pk):
    # --- Token + role verification (same as your edit view) ---
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
    except SignatureExpired:
        return redirect("unauthorized")
    except BadSignature:
        return redirect("unauthorized")

    if role != token_role:
        return redirect("unauthorized")

    profile_from_token = UserProfile.objects.get(user__id=user_uuid)
    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    # Fetch project where PM is the assigned project manager
    project = get_object_or_404(ProjectProfile, pk=pk, project_manager=profile_from_token)

    return render(request, 'project_profiling/project_view.html', {
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })

    
@login_required
@verified_email_required
@role_required('PM', 'OM')
def project_create(request, token, role, project_type):
    
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
    except SignatureExpired:
        return HttpResponse("Token expired")
    except BadSignature:
        return HttpResponse("Invalid token")

    if role != token_role:
        return HttpResponse("Role mismatch")

    try:
        profile_from_token = UserProfile.objects.get(user__id=user_uuid)
    except UserProfile.DoesNotExist:
        return HttpResponse("Invalid profile in token")

    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    # --- Select proper form ---
    if project_type == 'GC':
        FormClass = GeneralContractorForm
        initial_source = 'GC'
    elif project_type == 'DC':
        FormClass = DirectClientForm
        initial_source = 'DC'
    else:
        return HttpResponse("Invalid project type")

    if request.method == "POST":
        post_data = request.POST.copy()
        manager_id_list = post_data.pop("project_manager", [None])
        manager_id = manager_id_list[0] if manager_id_list else None

        if not post_data.get("status"):
            post_data["status"] = "PL"

        form = FormClass(post_data, request.FILES)

        print("DEBUG FULL POST DATA:", request.POST.dict())
        print("DEBUG manager_id =", manager_id)

        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = profile_from_token

            if manager_id:
                try:
                    project.project_manager = UserProfile.objects.get(id=int(manager_id))
                    
                except (UserProfile.DoesNotExist, ValueError, TypeError):
                    messages.error(request, "Selected Project Manager does not exist.")
                   
                    return render(request, 'project_profiling/project_form.html', {
                        'form': form,
                        'project_type': initial_source,
                        'dashboard_token': token,
                        'role': role,
                    })
            else:
                project.project_manager = None

            project.save()
            return redirect('project_list', token=token, role=role)

        else:
            print("DEBUG form errors:", form.errors)

    else:
        form = FormClass(initial={'project_source': initial_source})

    # --- Render default form ---
    return render(request, 'project_profiling/project_form.html', {
        'form': form,
        'project_type': initial_source,
        'dashboard_token': token,
        'role': role,
    })

@verified_email_required
@role_required('PM', 'OM')
def project_edit_signed_with_role(request, token, role, project_type, pk):
    # --- Token + role verification ---
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
        print("DEBUG: payload =", payload)
    except SignatureExpired:
        return HttpResponse("Token expired")
    except BadSignature:
        return HttpResponse("Invalid token")

    print(f"DEBUG: role={role}, token_role={token_role}")

    if role != token_role:
        return HttpResponse("Role mismatch")

    try:
        profile_from_token = UserProfile.objects.get(user__id=user_uuid)
        print("DEBUG: profile_from_token =", profile_from_token)
    except UserProfile.DoesNotExist:
        return HttpResponse("Invalid profile in token")

    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    # --- Fetch project ---
    if profile_from_token.role == 'EG':  # super admin can delete any project
        project = get_object_or_404(ProjectProfile, pk=pk)
    else:  # PM or OM
        project = get_object_or_404(
        ProjectProfile.objects.filter(
            Q(created_by=profile_from_token) | 
            Q(assigned_to=profile_from_token) | 
            Q(project_manager=profile_from_token),
            pk=pk
        )
    )

    print("DEBUG: editing project =", project)

    # --- Handle form submission ---
    if request.method == 'POST':
        post_data = request.POST.copy()  # make mutable for assignment

        # Handle project_manager ID to actual instance
        pm_id = post_data.get('project_manager')
        if pm_id:
            try:
                pm_instance = UserProfile.objects.get(id=pm_id)
                post_data['project_manager'] = pm_instance.id
                print("DEBUG: assigned project_manager =", pm_instance)
            except UserProfile.DoesNotExist:
                post_data['project_manager'] = None
                print("DEBUG: project_manager ID invalid")

        form = ProjectProfileForm(post_data, request.FILES, instance=project)

        print("DEBUG: POST data =", post_data)
        print("DEBUG: form.is_valid() =", form.is_valid())

        if not form.is_valid():
            print("DEBUG: form errors =", form.errors)

        if form.is_valid():
            # Set default status if missing
            if not form.cleaned_data.get('status'):
                form.instance.status = 'Pending'
                print("DEBUG: setting default status = Pending")

            form.save()
            messages.success(request, "Project updated successfully.")
            return redirect('project_list', token=token, role=role)
    else:
        form = ProjectProfileForm(instance=project)
        print("DEBUG: GET form instance =", form.instance)

    return render(request, 'project_profiling/project_edit.html', {
        'form': form,
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })


@login_required
@verified_email_required
@role_required('PM', 'OM')
def project_delete_signed_with_role(request, token, role, project_type, pk):
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload['u']
        token_role = payload['r']
    except SignatureExpired:
        return HttpResponse("Token expired")
    except BadSignature:
        return HttpResponse("Invalid token")

    if role != token_role:
        return HttpResponse("Role mismatch")

    try:
        profile_from_token = UserProfile.objects.get(user__id=user_uuid)
    except UserProfile.DoesNotExist:
        return HttpResponse("Invalid profile in token")

    if request.user.id != profile_from_token.user.id:
        messages.error(request, "This link does not belong to your account.")
        return redirect("unauthorized")

    # --- Fetch project ---
    if profile_from_token.role == 'EG':  # super admin can delete any project
        project = get_object_or_404(ProjectProfile, pk=pk)
    else:  # PM or OM
        project = get_object_or_404(
        ProjectProfile.objects.filter(
            Q(created_by=profile_from_token) | 
            Q(assigned_to=profile_from_token) | 
            Q(project_manager=profile_from_token),
            pk=pk
        )
    )

    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect('project_list', token=token, role=role)

    return render(request, 'project_profiling/project_confirm_delete.html', {
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })
