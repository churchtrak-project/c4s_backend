from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'churches', views.ChurchViewSet, basename='church')
router.register(r'pastors', views.PastorViewSet, basename='pastor')
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'resources', views.ResourceViewSet, basename='resource')
router.register(r'assessments', views.WellnessAssessmentViewSet, basename='assessment')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.PlatformStatsView.as_view(), name='platform-stats'),
]