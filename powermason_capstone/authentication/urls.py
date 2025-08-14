from django.urls import path
from allauth.account.views import LogoutView
from . import views
from .views import CustomPasswordChangeView

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
  
    path('unauthorized/', views.unauthorized, name='unauthorized'),
    
    path('logout/', LogoutView.as_view, name='account_logout'),
    
    path('accouts/login/', views.login, name='login'),
    
    path('accounts/email-verification-required/', views.email_verification_required, name='email_verification_required'),
    
    path('accounts/profile/', views.profile, name='profile'),
    
    path('accounts/settings/', views.settings, name='settings'),
    
    path('accounts/password/change/', CustomPasswordChangeView.as_view(), name='account_change_password'),
    
    path('manage-user-profiles/', views.manage_user_profiles, name='manage_user_profiles'),
    
    path('search-users/', views.search_users, name='search_users'),
]