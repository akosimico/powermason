from django import forms
from .models import ProjectProfile, ProjectBudget
from django.db.models import Q
from authentication.models import UserProfile


class ProjectProfileForm(forms.ModelForm):
    """Base form for all projects."""
    
    class Meta:
        model = ProjectProfile
        fields = [
            "project_manager",
            "assigned_to",
            "project_source",
            "project_code",
            "project_name",
            "project_type",
            "project_category",
            "description",
            "location",
            "gps_coordinates",
            "city_province",
            "start_date",
            "target_completion_date",
            "actual_completion_date",
            "estimated_cost",
            "expense",
            "payment_terms",
            "site_engineer",
            "subcontractors",
            "contract_agreement",
            "permits_licenses",
            "status",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "target_completion_date": forms.DateInput(attrs={"type": "date"}),
            "actual_completion_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["project_source"].widget = forms.TextInput(attrs={"readonly": "readonly"})
        self.fields["project_manager"].required = False

    # Base queryset: all PMs
        qs = UserProfile.objects.filter(role='PM')

    # Include current instance manager (if editing)
        if self.instance and self.instance.project_manager:
            qs = qs | UserProfile.objects.filter(id=self.instance.project_manager.id)

    # Include posted ID (if present)
        new_pm_id = self.data.get("project_manager")
        try:
            new_pm_id = int(new_pm_id)
            qs = qs | UserProfile.objects.filter(id=new_pm_id)
        except (TypeError, ValueError):
            pass

    # Assign final queryset
        self.fields["project_manager"].queryset = qs.distinct()





class GeneralContractorForm(ProjectProfileForm):
    """Form for General Contractor projects (GC)."""

    class Meta(ProjectProfileForm.Meta):
        model = ProjectProfile
        fields = ProjectProfileForm.Meta.fields + [
            "gc_company_name",
            "gc_license_number",
            "gc_contact_person",
            "gc_contact_number",
            "gc_contact_email",
        ]
        


class DirectClientForm(ProjectProfileForm):
    """Form for Direct Client projects (DC)."""

    class Meta(ProjectProfileForm.Meta):
        model = ProjectProfile
        fields = ProjectProfileForm.Meta.fields + [
            "client_name",
            "client_address",
            "client_contact_person",
            "client_contact_number",
            "client_contact_email",
        ]

class ProjectBudgetForm(forms.ModelForm):
    class Meta:
        model = ProjectBudget
        fields = ["category", "planned_amount"]
        widgets = {
            "category": forms.Select(attrs={
                "class": "w-full rounded-lg border border-gray-400 bg-white px-3 py-3 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500 text-gray-700",
            }),
            "planned_amount": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-gray-400 bg-white px-3 py-3 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500 text-gray-700",
                "placeholder": "Enter planned amount",
            }),
        }
