from django import forms
from .models import ProjectProfile

class ProjectProfileForm(forms.ModelForm):
    class Meta:
        model = ProjectProfile
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_completion_date': forms.DateInput(attrs={'type': 'date'}),
        }