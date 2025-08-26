from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list_default, name='project_list_default'),

    path('<str:token>/list/<str:role>/', views.project_list_signed_with_role, name='project_list'),
    
    path('<str:token>/create/<str:role>/<str:project_type>/', views.project_create, name='project_create'),
    
    path('<str:token>/edit/<str:role>/<str:project_type>/<int:pk>/', views.project_edit_signed_with_role, name='project_edit'),
    
    path('<str:token>/delete/<str:role>/<str:project_type>/<int:pk>/', views.project_delete_signed_with_role, name='project_delete'),
    
    path('<str:token>/view/<str:role>/<str:project_type>/<int:pk>/', views.project_view, name='project_view'),
    
    path('search/project-managers/', views.search_project_managers, name='search_project_managers'),

    path("<str:token>/<int:project_id>/<str:role>/budgets/", views.project_budgets, name="project_budgets"),
   
    path("<str:token>/costing/<str:role>/", views.project_costing_dashboard, name="project_costing_dashboard"),

    path("<str:token>/<int:project_id>/<str:role>/budgets/<int:budget_id>/delete/",views.delete_budget,name="delete_budget"),

    path(
        "<str:token>/<str:role>/<int:project_id>/set-approved-budget/",
        views.set_approved_budget,
        name="set_approved_budget",
    ),
    path(
    "<str:token>/<str:role>/<int:project_id>/allocate-funds/<int:budget_id>/",
    views.allocate_funds,
    name="allocate_funds",
),
    
      # Dashboard
    path('projects/<str:token>/<str:role>/<int:project_id>/allocate/', views.project_allocate_budget, name='project_allocate_budget'),

    # Allocate funds to a specific category
    path('projects/<str:token>/<str:role>/<int:project_id>/allocate/<int:budget_id>/', 
         views.allocate_fund_to_category, name='allocate_fund_to_category'),

path('projects/<str:token>/<str:role>/allocate/delete/<int:allocation_id>/', views.delete_allocation, name='delete_allocation'),


]
