from django.db import models
from project_profiling.models import ProjectProfile  # link to your existing project profiles
from authentication.models import UserProfile       # link to users

class ProjectTask(models.Model):
    project = models.ForeignKey(
        ProjectProfile, on_delete=models.CASCADE, related_name="tasks"
    )
    task_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Extra details for scheduling
    scope = models.CharField(max_length=255, blank=True, null=True)      # e.g., Electrical works

    assigned_to = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)  # e.g., 3.0
    manhours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)      # e.g., 120.0

    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight contribution to project (%)")
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Current approved progress % for this task")
    dependencies = models.ManyToManyField("self", symmetrical=False, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_name} ({self.project.project_name})"

class ProgressReport(models.Model):
    project = models.ForeignKey(ProjectProfile, on_delete=models.CASCADE, related_name="progress_reports")
    report_date = models.CharField(max_length=50, null=True, blank=True)  # can change to DateField if your PDF always has proper dates
    accomplished_to_date = models.CharField(max_length=50, null=True, blank=True)
    accomplished_before = models.CharField(max_length=50, null=True, blank=True)
    accomplished_this_period = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.project_code} - {self.report_date}"
    
    
class ProgressUpdate(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pending'),
        ('A', 'Approved'),
        ('R', 'Rejected'),
    ]

    task = models.ForeignKey(ProjectTask, on_delete=models.CASCADE, related_name="updates")
    reported_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name="updates_made")
    
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 45.00
    remarks = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    reviewed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="updates_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.task_name} - {self.progress_percent}% ({self.get_status_display()})"

class ProgressFile(models.Model):
    update = models.ForeignKey(
    ProgressUpdate, 
    on_delete=models.CASCADE, 
    related_name="attachments",
    null=True, 
    blank=True
)
    file = models.FileField(upload_to="progress_proofs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class SystemReport(models.Model):
    REPORT_TYPES = [
        ('D', 'Daily'),
        ('W', 'Weekly'),
        ('M', 'Monthly'),
        ('O', 'On-Demand'),
    ]

    project = models.ForeignKey(ProjectProfile, on_delete=models.CASCADE, related_name="system_reports")
    report_type = models.CharField(max_length=1, choices=REPORT_TYPES)
    file = models.FileField(upload_to="auto_reports/")
    generated_at = models.DateTimeField(auto_now_add=True)
