from django.db import models
from authentication.models import UserProfile


class ProjectProfile(models.Model):
    
    PROJECT_SOURCES = [
        ('GC', 'General Contractor'),
        ('DC', 'Direct Client')
    ]
    PROJECT_TYPES = [
        ('RES', 'Residential'),
        ('COM', 'Commercial'),
        ('IND', 'Industrial'),
        ('OTH', 'Other'),
    ]

    PROJECT_CATEGORIES = [
        ('PUB', 'Public'),
        ('PRI', 'Private'),
        ('REN', 'Renovation'),
        ('NEW', 'New Build'),
    ]

    STATUS_CHOICES = [
        ('PL', 'Planned'),
        ('OG', 'Ongoing'),
        ('CP', 'Completed'),
        ('CN', 'Cancelled'),
    ]

    created_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="projects_created"
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
    limit_choices_to={'role': 'PM'}
)

    # ----------------------------
    # 1. General Project Information
    # ----------------------------
    project_source = models.CharField(max_length=20, choices=PROJECT_SOURCES)
    project_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    project_name = models.CharField(max_length=200)
    project_type = models.CharField(max_length=10, choices=PROJECT_TYPES)
    project_category = models.CharField(max_length=10, choices=PROJECT_CATEGORIES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # ----------------------------
    # 2A. Contractor Information (GC projects)
    # ----------------------------
    gc_company_name = models.CharField(max_length=200, blank=True, null=True)
    gc_license_number = models.CharField(max_length=100, blank=True, null=True)
    gc_contact_person = models.CharField(max_length=200, blank=True, null=True)
    gc_contact_number = models.CharField(max_length=50, blank=True, null=True)
    gc_contact_email = models.EmailField(blank=True, null=True)

    # ----------------------------
    # 2B. Client Information (Direct Client projects)
    # ----------------------------
    client_name = models.CharField(max_length=200, blank=True, null=True)
    client_address = models.CharField(max_length=300, blank=True, null=True)
    client_contact_person = models.CharField(max_length=200, blank=True, null=True)
    client_contact_number = models.CharField(max_length=50, blank=True, null=True)
    client_contact_email = models.EmailField(blank=True, null=True)

    # ----------------------------
    # 3. Location
    # ----------------------------
    location = models.CharField(max_length=300)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    city_province = models.CharField(max_length=200, blank=True, null=True)

    # ----------------------------
    # 4. Timeline
    # ----------------------------
    start_date = models.DateField(blank=True, null=True)
    target_completion_date = models.DateField(blank=True, null=True)
    actual_completion_date = models.DateField(blank=True, null=True)

    # ----------------------------
    # 5. Financials
    # ----------------------------
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    approved_budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    allocated_funds = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    expense = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    payment_terms = models.TextField(blank=True, null=True)

    # ----------------------------
    # 6. Stakeholders
    # ----------------------------
    site_engineer = models.CharField(max_length=200, blank=True, null=True)
    subcontractors = models.TextField(blank=True, null=True)

    # ----------------------------
    # 7. Documentation
    # ----------------------------
    contract_agreement = models.FileField(upload_to="contracts/", blank=True, null=True)
    permits_licenses = models.FileField(upload_to="permits/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PL", 
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project_code or 'NoCode'} - {self.project_name}"

class ProjectFile(models.Model):
    project = models.ForeignKey(ProjectProfile, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="project_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)