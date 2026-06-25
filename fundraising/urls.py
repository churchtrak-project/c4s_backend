from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    # Public + authenticated campaign + donation endpoints (Phase 1)
    path('', include(router.urls)),

    # Guest donation initiation (no auth required)
    path('donate/', views.InitiateDonationView.as_view(), name='initiate-donation'),

    # Public campaign detail by uuid (for share links)
    path('public/campaigns/<uuid:public_uuid>/', views.PublicCampaignDetailView.as_view(), name='public-campaign'),

    # Simple ledger summary (can be public per campaign or authenticated)
    path('campaigns/<int:pk>/ledger/', views.CampaignLedgerView.as_view(), name='campaign-ledger'),
]