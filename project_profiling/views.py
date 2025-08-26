from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, SignatureExpired
from authentication.utils.tokens import parse_dashboard_token, make_dashboard_token
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
from django.db.models import Q
from django.http import HttpResponseRedirect
from decimal import Decimal, InvalidOperation
from django.db import models
from django.db.models import Sum
from django.views.decorators.http import require_POST
from authentication.models import UserProfile
from authentication.views import verify_user_token
from authentication.utils.decorators import verified_email_required, role_required
from .forms import ProjectProfileForm, GeneralContractorForm, DirectClientForm, ProjectBudgetForm

from .models import ProjectProfile, ProjectFile, ProjectBudget, FundAllocation

# ----------------------------------------
# FUNCTION
# ----------------------------------------
@login_required
@verified_email_required
@role_required('OM', 'EG')
def search_project_managers(request):
    query = request.GET.get('q', '')
    project_managers = UserProfile.objects.filter(role='PM').select_related("user")

    if query:
        project_managers = project_managers.filter(
            Q(full_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )

    data = [
        {
            "id": u.id, 
            "username": u.user.username,
            "full_name": u.full_name,
            "email": u.user.email,
        }
        for u in project_managers
    ]
    return JsonResponse(data, safe=False)


# ----------------------------------------
# PROJECTS LISTS / CREATE / EDIT / DELETE
# ----------------------------------------

@login_required
def project_list_default(request):
    
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    token = make_dashboard_token(profile)
    role = profile.role

    # Redirect to /projects/<token>/list/<role>/
    return redirect('project_list', token=token, role=role)

@login_required
@verified_email_required
@role_required('PM', 'OM', 'EG')
def project_list_signed_with_role(request, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile

    # Handle file upload
    if request.method == "POST" and "project_id" in request.POST:
        project_id = request.POST.get("project_id")
        project = get_object_or_404(ProjectProfile, id=project_id)

        if role == "PM" and project.project_manager != verified_profile:
            return HttpResponse("Unauthorized upload")
        if role == "OM" and not (project.created_by == verified_profile or project.assigned_to == verified_profile):
            return HttpResponse("Unauthorized upload")

        files = request.FILES.getlist("file")
        for f in files:
            ProjectFile.objects.create(project=project, file=f)

        return redirect("project_list_signed_with_role", token=token, role=role)

    # Fetch projects
    if verified_profile.role in ['EG', 'OM']:
        projects = ProjectProfile.objects.all()
    elif verified_profile.role == 'PM':
        projects = ProjectProfile.objects.filter(project_manager=verified_profile)
    else:
        projects = ProjectProfile.objects.filter(
            Q(created_by=verified_profile) | Q(assigned_to=verified_profile)
        ).distinct()

    context = {
        'dashboard_token': token,
        'user_uuid': verified_profile.user.id,  # fixed
        'role': role,
        'projects': projects,
    }
    return render(request, 'project_profiling/project_list.html', context)

@login_required
@verified_email_required
@role_required('OM', 'EG')
def project_costing_dashboard(request, token, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    projects = ProjectProfile.objects.all()

    projects_with_totals = []
    grand_total_planned = 0
    grand_total_allocated = 0

    for project in projects:
        # Sum of planned amounts
        total_planned = project.budgets.aggregate(total=Sum('planned_amount'))['total'] or 0

        # Sum of all allocations across categories
        total_allocated = sum(
            budget.allocations.aggregate(total=Sum('amount'))['total'] or 0
            for budget in project.budgets.all()
        )

        projects_with_totals.append({
            "project": project,
            "total_planned": total_planned,
            "total_allocated": total_allocated,
            "remaining": total_planned - total_allocated,
        })

        grand_total_planned += total_planned
        grand_total_allocated += total_allocated

    context = {
        "projects_with_totals": projects_with_totals,
        "grand_total_budget": grand_total_planned,
        "grand_total_allocated": grand_total_allocated,
        "token": token,
        "role": role,
    }
    return render(request, "project_profiling/project_costing_dashboard.html", context)

@login_required
@verified_email_required
def project_view(request, token, role, project_type, pk):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponseRedirect):
        return verified_profile

    # Now verified_profile is guaranteed to be a user/profile object
    user_role = verified_profile.role

    # Fetch project where PM is the assigned project manager
    if role == "PM":
        project = get_object_or_404(ProjectProfile, pk=pk, project_manager=verified_profile)
    else:
        project = get_object_or_404(ProjectProfile, pk=pk)


    return render(request, 'project_profiling/project_view.html', {
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })

    
@login_required
@verified_email_required
@role_required('EG', 'OM')
def project_create(request, token, role, project_type):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile

    # --- Select proper form ---
    if project_type == 'GC':
        FormClass = GeneralContractorForm
        initial_source = 'GC'
    elif project_type == 'DC':
        FormClass = DirectClientForm
        initial_source = 'DC'
    else:
        return HttpResponse("Invalid project type")

    if request.method == "POST":
        post_data = request.POST.copy()
        manager_id_list = post_data.pop("project_manager", [None])
        manager_id = manager_id_list[0] if manager_id_list else None

        if not post_data.get("status"):
            post_data["status"] = "PL"

        form = FormClass(post_data, request.FILES)

        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = verified_profile

            if manager_id:
                try:
                    project.project_manager = UserProfile.objects.get(id=int(manager_id))
                except (UserProfile.DoesNotExist, ValueError, TypeError):
                    messages.error(request, "Selected Project Manager does not exist.")
                    return render(request, 'project_profiling/project_form.html', {
                        'form': form,
                        'project_type': initial_source,
                        'dashboard_token': token,
                        'role': role,
                    })
            else:
                project.project_manager = None

            project.save()
            messages.success(request, "Project created successfully")
            return redirect('project_list', token=token, role=role)

        else:
            print("DEBUG form errors:", form.errors)
            # Notify user in UI
            messages.error(request, "There were errors in your form. Please check and try again.")

    else:
        form = FormClass(initial={'project_source': initial_source})

    # --- Render default form ---
    return render(request, 'project_profiling/project_form.html', {
        'form': form,
        'project_type': initial_source,
        'dashboard_token': token,
        'role': role,
    })
    
@verified_email_required
@role_required('PM', 'OM')
def project_edit_signed_with_role(request, token, role, project_type, pk):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile
    # --- Fetch project ---
    if verified_profile.role == 'EG':  # super admin can delete any project
        project = get_object_or_404(ProjectProfile, pk=pk)
    else:  # PM or OM
        project = get_object_or_404(
        ProjectProfile.objects.filter(
            Q(created_by=verified_profile) | 
            Q(assigned_to=verified_profile) | 
            Q(project_manager=verified_profile),
            pk=pk
        )
    )

    # --- Handle form submission ---
    if request.method == 'POST':
        post_data = request.POST.copy()  
        pm_id = post_data.get('project_manager')
        if pm_id:
            try:
                pm_instance = UserProfile.objects.get(id=pm_id)
                post_data['project_manager'] = pm_instance.id
            except UserProfile.DoesNotExist:
                post_data['project_manager'] = None

        form = ProjectProfileForm(post_data, request.FILES, instance=project)

        if not form.is_valid():
            print("DEBUG: form errors =", form.errors)

        if form.is_valid():
            # Set default status if missing
            if not form.cleaned_data.get('status'):
                form.instance.status = 'Pending'

            form.save()
            messages.success(request, "Project updated successfully.")
            return redirect('project_list', token=token, role=role)
    else:
        form = ProjectProfileForm(instance=project)

    return render(request, 'project_profiling/project_edit.html', {
        'form': form,
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })


@login_required
@verified_email_required
@role_required('EG', 'OM')
def project_delete_signed_with_role(request, token, role, project_type, pk):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile
    # --- Fetch project ---
    if verified_profile.role == 'EG':  # super admin can delete any project
        project = get_object_or_404(ProjectProfile, pk=pk)
    else:  # PM or OM
        project = get_object_or_404(
        ProjectProfile.objects.filter(
            Q(created_by=verified_profile) | 
            Q(assigned_to=verified_profile) | 
            Q(project_manager=verified_profile),
            pk=pk
        )
    )

    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect('project_list', token=token, role=role)

    return render(request, 'project_profiling/project_confirm_delete.html', {
        'project': project,
        'dashboard_token': token,
        'role': role,
        'project_type': project_type,
    })
    

# ----------------------------------------------
# PROJECTS BUDGET 
# ----------------------------------------------
@login_required
@verified_email_required
@role_required('EG', 'OM')
def set_approved_budget(request, token, role, project_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile  

    project = get_object_or_404(ProjectProfile, id=project_id)

    if request.method == "POST":
        amount = request.POST.get("approved_budget") 
        remarks = request.POST.get("remarks")

        project.approved_budget = amount
        project.budget_status = "APPROVED"
        project.budget_remarks = remarks
        project.save()

        messages.success(request, "Approved budget has been set successfully.")
        return redirect("project_costing_dashboard", token=token, role=role)

    return render(request, "budgets/set_approved_budget_form.html", {
        "project": project,
        "token": token,
        "role": role,
    })

@login_required
@verified_email_required
@role_required("EG", "OM")
def project_budgets(request, token, project_id, role):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile        

    project = get_object_or_404(ProjectProfile, id=project_id)
    budgets = project.budgets.all()

    total_budget = budgets.aggregate(total=Sum("planned_amount"))["total"] or 0

    remaining_budget = (project.approved_budget or 0) - total_budget

    if request.method == "POST":
        form = ProjectBudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.project = project
            budget.save()
            messages.success(request, "Budget added successfully.")
            return redirect(
                "project_budgets",
                token=token,
                project_id=project.id,
                role=role
            )
        else:
            messages.error(request, "There was an error adding the budget. Please check the form.")
    else:
        form = ProjectBudgetForm()

    return render(request, "project_profiling/project_budgets.html", {
        "project": project,
        "budgets": budgets,
        "form": form,
        "token": token,
        "role": role,
        "total_budget": total_budget,
        "remaining_budget": remaining_budget,  
    })


@login_required
@verified_email_required
@role_required("EG", "OM")
def delete_budget(request, token, project_id, role, budget_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):  
        return verified_profile
    project = get_object_or_404(ProjectProfile, id=project_id)
    budget = get_object_or_404(ProjectBudget, id=budget_id, project=project)

    if request.method == "POST":
        budget.delete()
        messages.success(request, "Budget entry deleted successfully.")
        return redirect("project_budgets", token=token, project_id=project.id, role=role)

    return render(request, "project_profiling/confirm_delete_budget.html", {
        "project": project,
        "budget": budget,
        "token": token,
        "role": role,
    })

# ----------------------------------------
# PROJECTS ALLOCATION
# ----------------------------------------    

@login_required
@verified_email_required
@role_required("EG", "OM")
def delete_allocation(request, token, role, allocation_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    allocation = get_object_or_404(FundAllocation, id=allocation_id)
    budget = allocation.project_budget
    project = budget.project

    if request.method == "POST":
        allocation.delete()
        messages.success(request, "Allocation deleted successfully.")
        return redirect(
            "allocate_fund_to_category",
            token=token,
            role=role,
            project_id=project.id,
            budget_id=budget.id
        )

    return render(request, "budgets/confirm_delete_allocation.html", {
        "allocation": allocation,
        "budget": budget,
        "project": project,
        "token": token,
        "role": role,
    })
    
@login_required
@verified_email_required
@role_required("EG", "OM")
def allocate_fund_to_category(request, token, role, project_id, budget_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    budget = get_object_or_404(ProjectBudget, id=budget_id, project=project)

    if request.method == "POST":
        amount_str = request.POST.get("amount")
        note = request.POST.get("note", "")
        
        if not amount_str:
            messages.error(request, "Please enter an allocation amount.")
        else:
            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    messages.error(request, "Amount must be greater than zero.")
                elif amount > 9999999999999.99: 
                    messages.error(request, "Amount exceeds the maximum allowed (₱9,999,999,999,999.99).")
                else:
                    FundAllocation.objects.create(
                        project_budget=budget,
                        amount=amount,
                        note=note
                    )
                    messages.success(
                        request, 
                        f"₱{amount:,.2f} allocated to {budget.get_category_display()} successfully."
                    )
                    return redirect(
                        "allocate_fund_to_category",
                        token=token,
                        role=role,
                        project_id=project.id,
                        budget_id=budget.id
                    )
            except InvalidOperation:
                messages.error(request, "Invalid amount entered. Please enter a valid number.")

    # Sum of all allocations for this category
    total_allocated = budget.allocations.aggregate(total=models.Sum("amount"))["total"] or 0
    remaining = budget.planned_amount - total_allocated

    # Absolute value for overrun display
    remaining_abs = abs(remaining)

    # Calculate allocation percentage for progress bar
    if budget.planned_amount > 0:
        allocation_percent = min((total_allocated / budget.planned_amount) * 100, 100)
    else:
        allocation_percent = 0

    return render(request, "budgets/allocate_fund_category.html", {
    "project": project,
    "budget": budget,
    "total_allocated": total_allocated,
    "remaining": remaining,
    "remaining_abs": remaining_abs,      
    "allocation_percent": allocation_percent,
    "token": token,
    "role": role,
})

@login_required
@verified_email_required
@role_required("EG", "OM")    
def project_allocate_budget(request, token, role, project_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile

    project = get_object_or_404(ProjectProfile, id=project_id)
    budgets = project.budgets.all()  
    
    return render(request, "budgets/allocate_funds_form.html", {
        "project": project,
        "budgets": budgets,
        "token": token,
        "role": role,
    })

@login_required
@verified_email_required
@role_required("EG", "OM")
def allocate_funds(request, token, role, project_id, budget_id):
    verified_profile = verify_user_token(request, token, role)
    if isinstance(verified_profile, HttpResponse):
        return verified_profile  

    project = get_object_or_404(ProjectProfile, id=project_id)
    budget = get_object_or_404(ProjectBudget, id=budget_id, project=project)

    if request.method == "POST":
        amount = request.POST.get("amount")
        note = request.POST.get("note")

        try:
            amount_decimal = float(amount)
            if amount_decimal <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("allocate_funds", token=token, role=role, project_id=project.id, budget_id=budget.id)
        except ValueError:
            messages.error(request, "Invalid amount.")
            return redirect("allocate_funds", token=token, role=role, project_id=project.id, budget_id=budget.id)

        FundAllocation.objects.create(
            project_budget=budget,
            amount=amount_decimal,
            note=note
        )

        messages.success(request, f"₱{amount_decimal:,.2f} allocated to {budget.get_category_display()}.")
        return redirect("project_costing_dashboard", token=token, role=role)

    return render(request, "budgets/allocate_funds_form.html", {
        "project": project,
        "budget": budget,
        "token": token,
        "role": role,
    })
    
  
