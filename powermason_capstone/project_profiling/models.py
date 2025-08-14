from django.db import models

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

    # A. Project Identification
    project_source = models.CharField(max_length=20, choices=PROJECT_SOURCES)
    project_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    project_name = models.CharField(max_length=200)
    project_type = models.CharField(max_length=10, choices=PROJECT_TYPES)
    project_category = models.CharField(max_length=10, choices=PROJECT_CATEGORIES, blank=True, null=True)
    client_name = models.CharField(max_length=200, blank=True, null=True)

    # B. Location Details
    location = models.CharField(max_length=300)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)

    # C. Timeline
    start_date = models.DateField(blank=True, null=True)
    target_completion_date = models.DateField(blank=True, null=True)
    actual_completion_date = models.DateField(blank=True, null=True)
    
    # D. Personnel
    project_manager = models.CharField(max_length=200, blank=True, null=True)
    site_engineer = models.CharField(max_length=200, blank=True, null=True)

    # E. Financials
    budget = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_funds = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    expense = models.DecimalField(max_digits=15, decimal_places=2)
 
    # Status
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project_code} - {self.name}"
