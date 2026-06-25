from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'counselors', views.CounselorViewSet, basename='counselor')
router.register(r'cases', views.CounselingCaseViewSet, basename='case')
router.register(r'sessions', views.CounselingSessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]