from django.urls import path
from allauth.account.views import LogoutView
from . import views
from .views import CustomPasswordChangeView, redirect_to_dashboard

urlpatterns = [
    path('', views.redirect_to_dashboard, name='dashboard'),
    
    path('dashboard/<str:token>/<str:role>/', views.dashboard_signed_with_role, name='dashboard_signed_with_role'),

    path('unauthorized/', views.unauthorized, name='unauthorized'),
    
    path('logout/', LogoutView.as_view, name='account_logout'),
    
    path('accounts/email-verification-required/', views.email_verification_required, name='email_verification_required'),
    
    path('accounts/profile/', views.profile, name='profile'),
    
    path('accounts/settings/', views.settings, name='settings'),
    
    path('accounts/password/change/', CustomPasswordChangeView.as_view(), name='account_change_password'),
    
    path('manage-user-profiles/', views.manage_user_profiles, name='manage_user_profiles'),
    
    path('search-users/', views.search_users, name='search_users'),
    

]