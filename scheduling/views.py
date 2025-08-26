# Standard library
import os
import json
import tempfile
from decimal import Decimal

# Third-party libraries
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# Authentication utils & decorators
from authentication.views import verify_user_token
from authentication.models import UserProfile
from authentication.utils.tokens import parse_dashboard_token, SignatureExpired, BadSignature
from authentication.utils.decorators import verified_email_required, role_required

# Local app imports
from .models import ProjectTask, ProgressFile, ProgressUpdate
from .forms import ProjectTaskForm, ProgressUpdateForm
from .utils.pdf_reader import extract_project_info
from project_profiling.models import ProjectProfile
from project_profiling.utils import recalc_project_progress


def progress_history(request):
    """
    Global progress history with filters.
    """
    updates = ProgressUpdate.objects.select_related(
        "task__project", "reported_by", "reviewed_by"
    ).prefetch_related("attachments").order_by("-created_at")

    # --- Filters ---
    project_id = request.GET.get("project")
    status = request.GET.get("status")
    reporter_id = request.GET.get("reporter")

    if project_id and project_id.isdigit():
        updates = updates.filter(task__project_id=project_id)

    if status in ["P", "A", "R"]:
        updates = updates.filter(status=status)

    if reporter_id and reporter_id.isdigit():
        updates = updates.filter(reported_by_id=reporter_id)

    projects = ProjectProfile.objects.all()
    reporters = UserProfile.objects.all()

    return render(request, "progress/progress_history.html", {
        "updates": updates,
        "projects": projects,
        "reporters": reporters,
        "selected_project": project_id,
        "selected_status": status,
        "selected_reporter": reporter_id,
    })

@login_required
def submit_progress_update(request, token, task_id, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponseRedirect):
        return verified_profile

    # Now verified_profile is guaranteed to be a user/profile object
    user_role = verified_profile.role
    task = get_object_or_404(ProjectTask, id=task_id)

    if request.method == "POST":
        form = ProgressUpdateForm(request.POST)
        files = request.FILES.getlist("attachments")

        if form.is_valid():
            update = form.save(commit=False)
            update.task = task
            update.reported_by = verified_profile  
            update.save()

            for f in files:
                ProgressFile.objects.create(update=update, file=f)
                
            messages.success(request, "Your report has been submitted and is waiting for approval.")

            return redirect(reverse("task_list", kwargs={
                "project_id": task.project.id,
                "token": token,
                "role": role
            }))

    else:
        form = ProgressUpdateForm()

    return render(request, "progress/submit_update.html", {
        "form": form,
        "task": task,
        "role": role,
        "token": token,
    })


@login_required
@verified_email_required
@role_required("EG", "OM")
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
@verified_email_required
@role_required("EG", "OM")
def approve_update(request, update_id):
    update = get_object_or_404(ProgressUpdate, id=update_id)

    update.status = "A"
    update.reviewed_by = request.user.userprofile
    update.reviewed_at = timezone.now()
    update.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    task = update.task
    approved_updates = task.updates.filter(status="A")
    total_progress = sum(u.progress_percent for u in approved_updates)
    task.progress = min(total_progress, 100)

    if task.progress >= 100:
        task.is_completed = True
        task.status = "CP"
    elif task.progress > 0:
        task.is_completed = False
        task.status = "OG"
    else:
        task.is_completed = False
        task.status = "PL"

    task.save(update_fields=["progress", "is_completed", "status"])

    task.project.update_progress_from_tasks()

    messages.success(request, f"Progress update for '{task.task_name}' approved successfully.")
    return redirect("review_updates")

@login_required
@verified_email_required
@role_required("EG", "OM")
def reject_update(request, update_id):
    update = get_object_or_404(ProgressUpdate, id=update_id)
    update.status = "R"
    update.reviewed_by = request.user.userprofile
    update.reviewed_at = timezone.now()
    update.save()
    messages.warning(request, f"Progress update for '{update.task.task_name}' has been rejected.")

    return redirect("review_updates")


@login_required
@verified_email_required
@role_required("PM", "OM")
def task_list(request, project_id, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    
    if role == "PM":
        tasks = project.tasks.filter(assigned_to=request.user.userprofile)
    else:
        tasks = project.tasks.all()

    # Prefetch the latest approved progress for each task
    for task in tasks:
        latest_update = task.updates.filter(status='A').order_by('-created_at').first()
        task.latest_progress = latest_update.progress_percent if latest_update else 0
        task.is_completed = task.latest_progress >= 100  # mark as completed if 100%

    return render(request, "scheduling/task_list.html", {
        "project": project,
        "tasks": tasks,
        "token": token,
        "role": role,
    })

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
                messages.success(request, f"Task '{task.task_name}' was successfully created.")
                return redirect("task_list", project.id, token, role)
            else:
                messages.error(request, "Failed to create task. Please check the form and try again.")

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

                if imported_data:
                    messages.success(request, "PDF file imported successfully.")
                else:
                    messages.warning(request, "No valid data found in the uploaded PDF.")

            elif upload.name.endswith((".xls", ".xlsx")):
                imported_data = {"tasks": parse_excel(upload)}
                if imported_data.get("tasks"):
                    messages.success(request, "Excel file imported successfully.")
                else:
                    messages.warning(request, "No tasks found in the uploaded Excel file.")

            else:
                messages.error(request, "Unsupported file format. Please upload PDF or Excel.")

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

        global_scope = request.POST.get("global_scope") or None
        assigned_to_id = request.POST.get("global_assigned_to") or None
        assigned_user_global = (
            UserProfile.objects.filter(id=assigned_to_id).first()
            if assigned_to_id else None
        )

        task_objs = []
        for i in range(task_count):
            task_name = request.POST.get(f"task_name_{i}")
            if not task_name: 
                continue

            start_date = parse_date(request.POST.get(f"start_date_{i}"))
            end_date = parse_date(request.POST.get(f"end_date_{i}"))
            duration = request.POST.get(f"duration_days_{i}")
            manhours = request.POST.get(f"manhours_{i}")

            # Weight
            weight_str = request.POST.get(f"weight_{i}", "").strip()
            weight = float(weight_str) if weight_str else 0.0

            # Scope (per-task overrides global)
            scope_i = request.POST.get(f"scope_{i}") or None
            scope = scope_i if scope_i else global_scope

            # Assigned to (per-task overrides global)
            assigned_to_id_i = request.POST.get(f"assigned_to_{i}") or None
            assigned_user = (
                UserProfile.objects.filter(id=assigned_to_id_i).first()
                if assigned_to_id_i else assigned_user_global
            )

            task_objs.append(ProjectTask(
                project=project,
                task_name=task_name,
                start_date=start_date,
                end_date=end_date,
                duration_days=duration,
                manhours=manhours,
                weight=weight,
                scope=scope,
                assigned_to=assigned_user,
            ))

        if task_objs:
            ProjectTask.objects.bulk_create(task_objs)
        else:
            print("No tasks to save.")  # DEBUG

        return redirect("task_list", project.id, token, role)

    return redirect("task_create", project.id, token, role)


@login_required
@verified_email_required
@role_required("PM", "OM")
def task_update(request, project_id, token, role, task_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    task = get_object_or_404(ProjectTask, id=task_id, project=project)

    if request.method == "POST":
        form = ProjectTaskForm(request.POST, instance=task)
        assigned_to_id = request.POST.get("assigned_to")
        if form.is_valid():
            try:
                task = form.save(commit=False)
                if assigned_to_id:
                    task.assigned_to = UserProfile.objects.filter(id=assigned_to_id).first()
                task.save()
                messages.success(request, f"Task '{task.task_name}' updated successfully!")
                return redirect("task_list", project.id, token, role)
            except Exception as e:
                messages.error(request, f"Error updating task: {str(e)}")
        else:
            messages.error(request, "Invalid form data. Please correct the errors below.")
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
@role_required("EG", "OM")  
def task_bulk_delete(request, project_id, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)

    if request.method == "POST":
        task_ids = request.POST.getlist("task_ids")  
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
@role_required("EG", "OM")
def task_delete(request, project_id, token, role, task_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    task = get_object_or_404(ProjectTask, id=task_id, project=project)

    if request.method == "POST":
        try:
            task_name = task.task_name
            task.delete()
            messages.success(request, f"Task '{task_name}' has been deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting task: {str(e)}")
        return redirect("task_list", project.id, token, role)

    return render(request, "scheduling/task_confirm_delete.html", {
        "task": task,
        "project": project,
        "token": token,
        "role": role,
        
    })
    