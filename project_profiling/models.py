from django.db import models
from authentication.models import UserProfile
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from django.apps import apps

class ProjectProfile(models.Model):
    # ----------------------------
    # Choice Definitions
    # ----------------------------
    PROJECT_SOURCES = [
        ("GC", "General Contractor"),
        ("DC", "Direct Client"),
    ]
    PROJECT_TYPES = [
        ("RES", "Residential"),
        ("COM", "Commercial"),
        ("IND", "Industrial"),
        ("OTH", "Other"),
    ]
    PROJECT_CATEGORIES = [
        ("PUB", "Public"),
        ("PRI", "Private"),
        ("REN", "Renovation"),
        ("NEW", "New Build"),
    ]
    STATUS_CHOICES = [
        ("PL", "Planned"),
        ("OG", "Ongoing"),
        ("CP", "Completed"),
        ("CN", "Cancelled"),
    ]

    # ----------------------------
    # 1. User Assignments
    # ----------------------------
    created_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="projects_created",
    )
    assigned_to = models.ForeignKey(
        UserProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_assigned",
    )
    project_manager = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "PM"},
    )

    # ----------------------------
    # 2. General Project Information
    # ----------------------------
    project_source = models.CharField(max_length=20, choices=PROJECT_SOURCES)
    project_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    project_name = models.CharField(max_length=200)
    project_type = models.CharField(max_length=10, choices=PROJECT_TYPES)
    project_category = models.CharField(max_length=10, choices=PROJECT_CATEGORIES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # ----------------------------
    # 3. Contractor / Client Information
    # ----------------------------
    gc_company_name = models.CharField(max_length=200, blank=True, null=True)
    gc_license_number = models.CharField(max_length=100, blank=True, null=True)
    gc_contact_person = models.CharField(max_length=200, blank=True, null=True)
    gc_contact_number = models.CharField(max_length=50, blank=True, null=True)
    gc_contact_email = models.EmailField(blank=True, null=True)

    client_name = models.CharField(max_length=200, blank=True, null=True)
    client_address = models.CharField(max_length=300, blank=True, null=True)
    client_contact_person = models.CharField(max_length=200, blank=True, null=True)
    client_contact_number = models.CharField(max_length=50, blank=True, null=True)
    client_contact_email = models.EmailField(blank=True, null=True)

    # ----------------------------
    # 4. Location
    # ----------------------------
    location = models.CharField(max_length=300)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    city_province = models.CharField(max_length=200, blank=True, null=True)

    # ----------------------------
    # 5. Timeline
    # ----------------------------
    start_date = models.DateField(blank=True, null=True)
    target_completion_date = models.DateField(blank=True, null=True)
    actual_completion_date = models.DateField(blank=True, null=True)

    # ----------------------------
    # 6. Financials
    # ----------------------------
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    approved_budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    expense = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    payment_terms = models.TextField(blank=True, null=True)
    
    # ----------------------------
    # 7. Stakeholders
    # ----------------------------
    site_engineer = models.CharField(max_length=200, blank=True, null=True)
    subcontractors = models.TextField(blank=True, null=True)

    # ----------------------------
    # 8. Documentation
    # ----------------------------
    contract_agreement = models.FileField(upload_to="contracts/", blank=True, null=True)
    permits_licenses = models.FileField(upload_to="permits/", blank=True, null=True)

    # ----------------------------
    # 9. Status & Tracking
    # ----------------------------
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PL")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Overall project progress (%)"
    )

    # ----------------------------
    # Properties / Business Logic
    # ----------------------------
    def __str__(self):
        return f"{self.project_code or 'NoCode'} - {self.project_name}"

    @property
    def total_expenses(self):
        return sum(cost.amount for cost in self.costs.all())

    @property
    def cost_performance(self):
        """Return % of budget spent"""
        if not self.approved_budget or self.approved_budget == 0:
            return None
        return (self.total_expenses / self.approved_budget) * 100

    @property
    def total_task_allocations(self):
        TaskCost = apps.get_model("scheduling", "TaskCost")
        return sum(tc.allocated_amount for tc in TaskCost.objects.filter(task__project=self))

    @property
    def remaining_budget(self):
        return (self.approved_budget or 0) - self.total_task_allocations

    def save(self, *args, **kwargs):
        # Auto-mark completed when progress reaches 100
        if self.progress >= 100:
            self.is_completed = True
        else:
            self.is_completed = False
        super().save(*args, **kwargs)
        
    def update_progress_from_tasks(self):
        tasks = self.tasks.all()
        if tasks.exists():
            total_progress = sum(
            (task.progress or Decimal(0)) * (Decimal(task.weight) / Decimal(100))
            for task in tasks
            )
            self.progress = min(total_progress, Decimal(100))
        else:
            self.progress = Decimal(0)

    # Auto-update project status
        if self.progress >= 100:
            self.status = "CP"
        elif self.progress > 0:
            self.status = "OG"
        else:
            self.status = "PL"

        self.save(update_fields=["progress", "status"])

class ProjectFile(models.Model):
    project = models.ForeignKey(ProjectProfile, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="project_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
class CostCategory(models.TextChoices):
    LABOR = "LAB", "Labor"
    MATERIALS = "MAT", "Materials"
    EQUIPMENT = "EQP", "Equipment"
    SUBCONTRACTOR = "SUB", "Subcontractor"
    OTHER = "OTH", "Other"


# 1️⃣ Planned budget
class ProjectBudget(models.Model):
    project = models.ForeignKey("ProjectProfile", on_delete=models.CASCADE, related_name="budgets")
    category = models.CharField(max_length=3, choices=CostCategory.choices)
    planned_amount = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"[BUDGET] {self.project.project_name} - {self.get_category_display()} ({self.planned_amount})"



# 2️⃣ Actual expenditures (linked to tasks if needed)
class ProjectCost(models.Model):
    project = models.ForeignKey("ProjectProfile", on_delete=models.CASCADE, related_name="costs")
    category = models.CharField(max_length=3, choices=CostCategory.choices)
    description = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date_incurred = models.DateField(default=timezone.now)
    linked_task = models.ForeignKey(
        "scheduling.ProjectTask",
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_incurred"]

    def __str__(self):
        return f"[ACTUAL] {self.project.project_name} - {self.get_category_display()} ({self.amount})"

class FundAllocation(models.Model):
    project_budget = models.ForeignKey(
        "ProjectBudget", 
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date_allocated = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-date_allocated"]

    def __str__(self):
        return f"[ALLOC] {self.project_budget.project.project_name} - {self.project_budget.get_category_display()} ({self.amount})"
