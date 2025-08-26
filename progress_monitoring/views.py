from django.shortcuts import render, redirect
from django.contrib import messages
from project_profiling.models import ProjectProfile, ProjectBudget, ProjectCost
from scheduling.models import ProjectTask
from scheduling.views import verify_user_token

def progress_monitoring(request, token, role):
    # --- Verify token and get profile ---
    profile = verify_user_token(request, token, role)  

    # --- Fetch projects ---
    if profile.role == "PM":
        projects = ProjectProfile.objects.filter(project_manager=profile)
    else:
        projects = ProjectProfile.objects.all()

    # --- Prepare project data ---
    project_data = []
    for project in projects:
        tasks = ProjectTask.objects.filter(project=project).order_by("start_date")
        task_progress = [(task.task_name, round(task.progress, 2), task.weight) for task in tasks]

        total_weight = sum(task.weight for task in tasks) or 1
        total_progress = sum((task.progress * task.weight) for task in tasks) / total_weight

        project_data.append({
            "project_name": project.project_name,
            "project_status": project.status,
            "task_progress": task_progress,
            "total_progress": round(total_progress, 2),
        })

    context = {
        "projects": project_data,
        "token": token,
        "role": role,
    }

    return render(request, "progress/dashboard_projects_list.html", context)
