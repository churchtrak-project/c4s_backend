from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'campaigns', views.CampaignViewSet, basename='campaign')
router.register(r'campaign-updates', views.CampaignUpdateViewSet, basename='campaign-update')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'disbursements', views.DisbursementViewSet, basename='disbursement')

urlpatterns = [
    path('', include(router.urls)),

    path('dashboard/', views.FundDashboardView.as_view(), name='fund-dashboard'),
    path('donate/', views.InitiateDonationView.as_view(), name='initiate-donation'),
    path('donations/<int:pk>/resend-receipt/', views.ResendReceiptView.as_view(), name='resend-receipt'),

    path('public/campaigns/<uuid:public_uuid>/', views.PublicCampaignDetailView.as_view(), name='public-campaign'),
    path('public/campaigns/<uuid:public_uuid>/ledger/', views.PublicCampaignLedgerView.as_view(), name='public-campaign-ledger'),

    path('campaigns/<int:pk>/ledger/', views.CampaignLedgerView.as_view(), name='campaign-ledger'),
]