from django.urls import path

from . import views

urlpatterns = [
    # Self-signup for a new church (public)
    path('church-signup/', views.ChurchSignupView.as_view(), name='church-signup'),
    # Login for all roles (email or phone + pw) - returns token + profile
    path('login/', views.LoginView.as_view(), name='login'),
    path('me/', views.MeView.as_view(), name='me'),
]