from django.urls import path
from . import views

urlpatterns = [
    # ---------------------------
    # Scheduling / Tasks
    # ---------------------------
    path('<int:project_id>/<str:token>/<str:role>/tasks/', views.task_list, name='task_list'),
    path("<int:project_id>/<str:token>/<str:role>/tasks/add/", views.task_create, name="task_create"),
    path("<int:project_id>/<str:token>/<str:role>/tasks/save-imported/", views.save_imported_tasks, name="save_imported_tasks"),
    path("<int:project_id>/<str:token>/<str:role>/tasks/<int:task_id>/update/",views.task_update, name="task_update"),
    path("<int:project_id>/<str:token>/<str:role>/tasks/<int:task_id>/delete/",views.task_delete, name="task_delete"),
    path("<int:project_id>/<str:token>/<str:role>/tasks/bulk-delete/",views.task_bulk_delete, name="task_bulk_delete"),
    path("<str:token>/task/<int:task_id>/submit-progress/<str:role>/", views.submit_progress_update, name="submit_progress"),

    # ---------------------------
    # Progress Review
    # ---------------------------
    path('progress/review/', views.review_updates, name='review_updates'),
    path('progress/approve/<int:update_id>/', views.approve_update, name='approve_update'),
    path('progress/reject/<int:update_id>/', views.reject_update, name='reject_update'),
    path("progress/history/", views.progress_history, name="progress_history"),

    
]
