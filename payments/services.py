"""
KeshoPay integration service (single merchant account).

Flow (per https://keshopay.co.ke/docs):
1. Generate authorizationKey server-side (NEVER expose private key)
2. POST to /api/v1/payment/initiate with key + details
3. On success response → redirect donor to checkoutUrl (or handle STK)
4. Handle webhook for final status and update our records

Reference + metadata are used to attribute the payment back to a specific Church / Campaign.
"""
import base64
import json
import time
from decimal import Decimal
from typing import Optional, Dict, Any

import requests
from django.conf import settings
from django.utils import timezone

from .models import PaymentTransaction


class KeshoPayError(Exception):
    pass


def _get_kesho_config():
    cfg = getattr(settings, 'KESHOPAY', {})
    if not cfg.get('PUBLIC_KEY') or not cfg.get('PRIVATE_KEY'):
        raise KeshoPayError("KeshoPay keys are not configured. Set KESHOPAY_PUBLIC_KEY and KESHOPAY_PRIVATE_KEY in .env")
    return cfg


def create_authorization_key(amount: Decimal, reference: str, wallet_id: Optional[str] = None) -> str:
    """
    Generate the exact authorization key format shown in KeshoPay docs.
    Must be called on the server with the private key.
    """
    cfg = _get_kesho_config()
    data = {
        "publicKey": cfg['PUBLIC_KEY'],
        "privateKey": cfg['PRIVATE_KEY'],
        "amount": float(amount),
        "walletId": wallet_id or cfg.get('WALLET_ID', ''),
        "timestamp": int(time.time() * 1000),
        "reference": reference,   # extra for our traceability
    }
    json_string = json.dumps(data, separators=(',', ':'))
    return base64.b64encode(json_string.encode('utf-8')).decode('utf-8')


def initiate_payment(
    amount: Decimal,
    phone_number: str,
    reference: str,
    redirect_url: str,
    currency: str = 'KES',
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calls KeshoPay /api/v1/payment/initiate.
    Returns the parsed response (expect success + checkoutUrl or similar).
    """
    cfg = _get_kesho_config()
    auth_key = create_authorization_key(amount, reference, cfg.get('WALLET_ID'))

    payload = {
        "authorizationKey": auth_key,
        "amount": float(amount),
        "reference": reference,
        "redirectUrl": redirect_url,
        "currency": currency,
        "phoneNumber": phone_number,
    }
    if metadata:
        payload["metadata"] = metadata

    url = f"{cfg['BASE_URL'].rstrip('/')}/api/v1/payment/initiate"

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise KeshoPayError(f"KeshoPay initiate failed: {str(e)}") from e

    return data


def record_transaction(
    *,
    church,
    direction: str,
    amount: Decimal,
    reference: str,
    phone_number: str = '',
    raw_request: Optional[dict] = None,
    raw_response: Optional[dict] = None,
    status: str = PaymentTransaction.STATUS_PENDING,
    related_donation=None,
    related_disbursement=None,
) -> PaymentTransaction:
    """Helper to persist an audit row."""
    return PaymentTransaction.objects.create(
        church=church,
        direction=direction,
        amount=amount,
        reference=reference,
        phone_number=phone_number,
        raw_request=raw_request or {},
        raw_response=raw_response or {},
        status=status,
        related_donation=related_donation,
        related_disbursement=related_disbursement,
    )
