from django.contrib import admin
from .models import ProjectProfile, ProjectBudget, ProjectCost

@admin.register(ProjectProfile)
class ProjectProfileAdmin(admin.ModelAdmin):
    list_display = (
        "project_name",              # changed from project_title
        "project_code",
        "project_type",
        "project_manager",
        "site_engineer",  
        "start_date",
        "target_completion_date",    # changed from end_date
        "approved_budget",
    )
    list_filter = ('project_source', 'project_type', 'status')
    search_fields = (
        'project_code', 
        'project_name', 
        'client_name', 
        'gc_company_name'
    )
    ordering = ('-created_at',)
    
@admin.register(ProjectBudget)
class ProjectBudgetAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "planned_amount")
    list_filter = ("category", "project")
    search_fields = ("project__name",)
    ordering = ("project", "category")


@admin.register(ProjectCost)
class ProjectCostAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "description", "amount", "date_incurred", "linked_task", "created_at")
    list_filter = ("category", "date_incurred", "project")
    search_fields = ("project__name", "description", "linked_task__task_name")
    date_hierarchy = "date_incurred"
    ordering = ("-date_incurred",)
