from django.contrib import admin
from .models import ProjectTask

from django.contrib import admin
from .models import ProjectTask

@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "task_name", "project", "start_date", "end_date", "get_progress")
    search_fields = ("task_name", "project__project_name")
    list_filter = ("project", "assigned_to")


    def get_progress(self, obj):
        # Get latest approved update
        latest_update = obj.updates.filter(status="A").order_by("-created_at").first()
        return f"{latest_update.progress_percent}%" if latest_update else "No updates"
    
    get_progress.short_description = "Progress"

 