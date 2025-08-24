from django.shortcuts import render, get_object_or_404, redirect
from .models import ProjectTask, ProgressFile, ProgressUpdate
from .forms import ProjectTaskForm, ProgressUpdateForm
from project_profiling.models import ProjectProfile
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from .utils.pdf_reader import extract_project_info
from authentication.models import UserProfile
from django.db.models import Q
from authentication.utils.tokens import parse_dashboard_token, SignatureExpired, BadSignature
import tempfile, os
import pandas as pd
import json
from django.utils.dateparse import parse_date
from authentication.utils.decorators import verified_email_required, role_required
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.utils import timezone

@login_required
def submit_progress_update(request, token, task_id, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  # check if verification failed
        return verified_profile

    task = get_object_or_404(ProjectTask, id=task_id)

    if request.method == "POST":
        form = ProgressUpdateForm(request.POST)
        files = request.FILES.getlist("attachments")

        if form.is_valid():
            update = form.save(commit=False)
            update.task = task
            update.reported_by = verified_profile  # use verified profile, not just request.user
            update.save()

            for f in files:
                ProgressFile.objects.create(update=update, file=f)

            return redirect("project_dashboard", project_id=task.project.id)

    else:
        form = ProgressUpdateForm()

    return render(request, "progress/submit_update.html", {
        "form": form,
        "task": task,
        "role": role,
        "token": token,
    })


@login_required
def review_updates(request):
    """
    Global view for OM/EG and superusers to see all pending updates.
    """
    pending_updates = ProgressUpdate.objects.filter(status="P")
    context = {
        "updates": pending_updates,
    }
    return render(request, "progress/review_updates.html", context)

@login_required
def approve_update(request, update_id):
    update = get_object_or_404(ProgressUpdate, id=update_id)
    update.status = "A"
    update.reviewed_by = request.user.userprofile
    update.reviewed_at = timezone.now()

    task = update.task
    task.progress = min(task.progress + update.progress_percent, 100)
    task.save()
    update.save()
    messages.success(request, f"Progress update for '{task.task_name}' approved successfully.")

    return redirect("review_updates")


@login_required
def reject_update(request, update_id):
    update = get_object_or_404(ProgressUpdate, id=update_id)
    update.status = "R"
    update.reviewed_by = request.user.userprofile
    update.reviewed_at = timezone.now()
    update.save()
    messages.warning(request, f"Progress update for '{update.task.task_name}' has been rejected.")

    return redirect("review_updates")
def get_project_managers():
    return UserProfile.objects.filter(role="PM")

@login_required
@verified_email_required
@role_required("PM", "OM")
def verify_user_token(request, token, role):
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

    return profile_from_token  # return verified profile

@login_required
@verified_email_required
@role_required("PM", "OM")
def task_list(request, project_id, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  # check if verification failed
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    tasks = project.tasks.all()
    return render(request, "scheduling/task_list.html", {
    "project": project,
    "tasks": tasks,
    "token": token,
    "role": role,
})


@login_required
@verified_email_required
@role_required("PM", "OM")
def parse_excel(file):
    df = pd.read_excel(file)
    tasks = []
    for _, row in df.iterrows():
        tasks.append({
            "task_name": row.get("Task"),
            "start_date": row.get("Start"),
            "end_date": row.get("End"),
            "duration_days": row.get("Days"),
            "manhours": row.get("MH"),
            "scope": row.get("Scope"),
        })
    return tasks

@login_required
@verified_email_required
@role_required("PM", "OM")
def task_create(request, project_id, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    imported_data = None
    form = ProjectTaskForm()

    if request.method == "POST":
        # --- Manual Save ---
        if "save_task" in request.POST:
            form = ProjectTaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.project = project
                task.save()
                form.save_m2m()
                return redirect("task_list", project.id, token, role)

        # --- Import File ---
        elif "import_file" in request.POST and request.FILES.get("upload_file"):
            upload = request.FILES["upload_file"]

            if upload.name.endswith(".pdf"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    for chunk in upload.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                imported_data = extract_project_info(tmp_path)  # dict
                os.remove(tmp_path)

            elif upload.name.endswith((".xls", ".xlsx")):
                imported_data = {"tasks": parse_excel(upload)}

    return render(request, "scheduling/task_form.html", {
    "form": form,
    "project": project,
    "imported_data": imported_data,
    "token": token,   
    "role": role,     
})

@login_required
@verified_email_required
@role_required("PM", "OM")
def save_imported_tasks(request, project_id, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)

    if request.method == "POST":
        task_count = int(request.POST.get("task_count", 0))
        imported_data = json.loads(request.POST.get("tasks_json", "[]"))

        # Normalize global inputs (convert "" -> None)
        global_scope = request.POST.get("global_scope") or None
        assigned_to_id = request.POST.get("global_assigned_to") or None
        assigned_user_global = (
            UserProfile.objects.filter(id=assigned_to_id).first()
            if assigned_to_id else None
        )

        task_objs = []
        for i in range(task_count):
            # Per-task scope first, fallback to global
            scope_i = request.POST.get(f"scope_{i}") or None
            scope = scope_i if scope_i else global_scope

            # Per-task assigned_to first, fallback to global
            assigned_to_id_i = request.POST.get(f"assigned_to_{i}") or None
            assigned_user = (
                UserProfile.objects.filter(id=assigned_to_id_i).first()
                if assigned_to_id_i else assigned_user_global
            )

        
            weight_str = request.POST.get(f"weight_{i}", "").strip()
            weight = float(weight_str) if weight_str else 0.0  

            task_objs.append(ProjectTask(
                project=project,
                task_name=imported_data[i].get("task_name"),
                start_date=parse_date(imported_data[i].get("start_date")),
                end_date=parse_date(imported_data[i].get("end_date")),
                duration_days=imported_data[i].get("duration_days"),
                manhours=imported_data[i].get("manhours"),
                weight=weight,   
                scope=scope,
                assigned_to=assigned_user,
            ))

        ProjectTask.objects.bulk_create(task_objs)
        return redirect("task_list", project.id, token, role)

    return redirect("task_create", project.id, token, role)

@login_required
@verified_email_required
@role_required("PM", "OM")
def task_update(request, project_id, token, role, task_id):
    project_managers = UserProfile.objects.filter(role="PM")
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    task = get_object_or_404(ProjectTask, id=task_id, project=project)

    if request.method == "POST":
        form = ProjectTaskForm(request.POST, instance=task)
        assigned_to_id = request.POST.get("assigned_to")
        if form.is_valid():
            task = form.save(commit=False)
            if assigned_to_id:
                task.assigned_to = UserProfile.objects.filter(id=assigned_to_id).first()
            task.save()
            return redirect("task_list", project.id, token, role)
    else:
        form = ProjectTaskForm(instance=task)

    return render(request, "scheduling/task_edit.html", {
        "form": form,
        "project": project,
        "task": task,
        "token": token,
        "role": role,
        "project_managers": UserProfile.objects.filter(role="PM"),
    })


@login_required
@verified_email_required
@role_required("PM", "OM")  # adjust roles if needed
def task_bulk_delete(request, project_id, token, role):
    # --- Token validation (same style as your other views) ---
    try:
        payload = parse_dashboard_token(token)
        user_uuid = payload["u"]
        token_role = payload["r"]
    except SignatureExpired:
        return HttpResponse("Token expired")
    except BadSignature:
        return HttpResponse("Invalid token")

    if role != token_role:
        return HttpResponseForbidden("Invalid role")

    project = get_object_or_404(ProjectProfile, id=project_id)

    if request.method == "POST":
        task_ids = request.POST.getlist("task_ids")  # all checked tasks
        if task_ids:
            deleted_count, _ = ProjectTask.objects.filter(
                id__in=task_ids, project=project
            ).delete()
            messages.success(request, f"Deleted {deleted_count} task(s).")
        else:
            messages.warning(request, "No tasks were selected.")

    return redirect("task_list", project.id, token, role)

@login_required
@verified_email_required
@role_required("PM", "OM")
def task_delete(request, project_id, token, role, task_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    task = get_object_or_404(ProjectTask, id=task_id, project=project)

    if request.method == "POST":
        task.delete()
        return redirect("task_list", project.id, token, role)

    return render(request, "scheduling/task_confirm_delete.html", {
        "task": task,
        "project": project,
        "token": token,
        "role": role,
        
    })
    