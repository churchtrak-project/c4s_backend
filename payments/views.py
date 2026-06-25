from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import PaymentTransaction
from .services import KeshoPayError, initiate_payment, record_transaction

from fundraising.models import Donation   # for linking on webhook


@method_decorator(csrf_exempt, name='dispatch')
class KeshoPayWebhookView(APIView):
    """
    Public webhook endpoint.
    KeshoPay will POST here on payment events.
    We MUST return 200 quickly.
    """

    authentication_classes = []   # public
    permission_classes = []

    def post(self, request):
        payload = request.data
        event = payload.get('event')
        data = payload.get('data', {})

        reference = data.get('reference')
        transaction_id = data.get('transactionId')
        amount = data.get('amount')
        status_from_provider = data.get('status', '').lower()

        if not reference:
            # Still ack so they don't retry forever
            return Response({'ok': True, 'message': 'no reference'}, status=status.HTTP_200_OK)

        # Try to find the related donation by our reference
        donation = Donation.objects.filter(kesho_reference=reference).first()

        # Create or update audit transaction
        church = donation.church if donation else None

        tx_status = PaymentTransaction.STATUS_SUCCESS if status_from_provider in ('successful', 'success') else PaymentTransaction.STATUS_FAILED

        tx = record_transaction(
            church=church or getattr(donation, 'church', None),  # fallback may be None on first webhooks
            direction=PaymentTransaction.DIRECTION_IN,
            amount=Decimal(str(amount)) if amount else Decimal('0'),
            reference=reference,
            phone_number=data.get('customer', {}).get('phoneNumber', ''),
            raw_response=payload,
            status=tx_status,
            related_donation=donation,
        )

        if donation:
            if status_from_provider in ('successful', 'success'):
                donation.status = Donation.STATUS_SUCCESS
                donation.provider_transaction_id = transaction_id or ''
                donation.received_at = timezone.now()
                donation.metadata = {**donation.metadata, 'webhook': payload}
                donation.save(update_fields=['status', 'provider_transaction_id', 'received_at', 'metadata', 'updated_at'])

                # TODO later: if linked to pledge, advance next_due_date etc.
            elif status_from_provider in ('failed', 'failure'):
                donation.status = Donation.STATUS_FAILED
                donation.metadata = {**donation.metadata, 'webhook': payload}
                donation.save(update_fields=['status', 'metadata', 'updated_at'])

        # Always acknowledge
        return Response({'ok': True}, status=status.HTTP_200_OK)


class InitiatePaymentView(APIView):
    """
    Thin helper (mainly for testing or internal admin-triggered payouts).
    Real donation flow goes through fundraising.InitiateDonationView which calls this logic.
    """

    def post(self, request):
        # Minimal protection - in real life add better auth for this endpoint
        try:
            amount = Decimal(str(request.data['amount']))
            phone = request.data['phone_number']
            reference = request.data['reference']
            redirect_url = request.data.get('redirect_url', 'https://example.com/thank-you')
            metadata = request.data.get('metadata', {})
        except (KeyError, ValueError, TypeError) as e:
            return Response({'error': f'Missing or invalid fields: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = initiate_payment(
                amount=amount,
                phone_number=phone,
                reference=reference,
                redirect_url=redirect_url,
                metadata=metadata,
            )
            return Response(result, status=status.HTTP_200_OK)
        except KeshoPayError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
