from django.contrib import admin
from .models import ProjectProfile

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
