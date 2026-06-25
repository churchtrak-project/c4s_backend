from django.urls import path

from . import views

urlpatterns = [
    # KeshoPay webhook - must be publicly reachable and return 200 quickly
    path('webhook/keshopay/', views.KeshoPayWebhookView.as_view(), name='keshopay-webhook'),

    # Optional helper to manually trigger initiate (for testing / admin flows)
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
]