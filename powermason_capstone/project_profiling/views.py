from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from authentication.decorators import verified_email_required, role_required
from .models import ProjectProfile
from .forms import ProjectProfileForm
from django.utils import timezone
from datetime import timedelta

@login_required
@verified_email_required
def project_list(request):
    return render (request, 'project_profiling/project_list.html')

@login_required
@verified_email_required
@role_required('OM')
def project_create(request):
    if request.method == 'POST':
        form = ProjectProfileForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('project_list')  # replace with your actual view name
    else:
        form = ProjectProfileForm()  # GET request, empty form

    # Render the form for GET or invalid POST
    return render(request, 'project_profiling/project_form.html', {'form': form})