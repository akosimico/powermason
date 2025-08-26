from django import forms
from .models import ProjectTask, ProgressUpdate, ProgressFile
from authentication.models import UserProfile  # adjust if your user model is elsewhere
from datetime import timedelta

class ProjectTaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ["scope", "assigned_to", "task_name", "start_date", "end_date", "duration_days", "manhours","weight"]

        labels = {
            "assigned_to": "Assign To",
            "scope": "Scope",
            "task_name": "Task",
            "start_date": "Start Date",
            "end_date": "End",
            "duration_days": "Days",
            "manhours": "Manhours",
            "weight": "Weight (%)",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "id": "id_start_date"}),
            "end_date": forms.DateInput(attrs={"type": "date", "id": "id_end_date"}),
           "duration_days": forms.NumberInput(attrs={
                "readonly": "readonly",
                "class": "w-full border-gray-300 rounded-md shadow-sm p-2 bg-gray-100 cursor-not-allowed",
                "id": "id_duration_days"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show only Project Managers
        self.fields["assigned_to"].queryset = UserProfile.objects.filter(role="PM")
        self.fields["assigned_to"].widget.attrs.update({
            "class": "select2 w-full",  # for searchable dropdown
            "data-placeholder": "Search Project Manager...",
        })

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")

        if start and end:
            if end < start:
                self.add_error("end_date", "End date cannot be earlier than start date.")
            else:
                # auto-calc days (end - start + 1)
                cleaned_data["duration_days"] = (end - start).days + 1

        return cleaned_data

class ProgressUpdateForm(forms.ModelForm):
    class Meta:
        model = ProgressUpdate
        fields = ["progress_percent", "remarks"]
        widgets = {
            "progress_percent": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500",
                "placeholder": "Enter % progress",
                "step": "0.01",
                "min": "0",
                "max": "100"
            }),
            "remarks": forms.Textarea(attrs={
                "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500",
                "placeholder": "Additional notes or remarks...",
                "rows": 3
            }),
        }