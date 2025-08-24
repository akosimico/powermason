from django.urls import path
from . import views


urlpatterns = [
    path('', views.project_list_default, name='project_list_default'),

    path('<str:token>/list/<str:role>/', views.project_list_signed_with_role, name='project_list'),
    
    path('<str:token>/create/<str:role>/<str:project_type>/', views.project_create,name='project_create'),
    
    path('<str:token>/edit/<str:role>/<str:project_type>/<int:pk>/', views.project_edit_signed_with_role, name='project_edit'),
    
    path('<str:token>/delete/<str:role>/<str:project_type>/<int:pk>/', views.project_delete_signed_with_role, name='project_delete'),
    
    path('<str:token>/view/<str:role>/<str:project_type>/<int:pk>/', views.project_view, name='project_view'),
    
    path('search/project-managers/', views.search_project_managers, name='search_project_managers'),
     # Project Dashboard
    path("<int:project_id>/dashboard/", views.project_dashboard, name="project_dashboard"),
]