from django.urls import path
from .views import progress_monitoring

urlpatterns = [
   path('<str:token>/<str:role>/', progress_monitoring, name='progress_monitoring')

]
