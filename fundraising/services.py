"""Non-view helpers for fundraising (receipt delivery stubs, etc.)."""


def send_donation_receipt(donation, channels=None):
    """
    Stub receipt delivery. Replace with Africa's Talking / SendGrid when ready.
    Returns a dict describing what would have been sent.
    """
    channels = channels or ['sms', 'email']
    phone = donation.donor_phone
    name = 'Anonymous' if donation.is_anonymous else (donation.donor_name or 'Friend')
    result = {}

    if 'sms' in channels:
        result['sms'] = {
            'sent': True,
            'stub': True,
            'to': phone,
            'message': (
                f"ShepherdCare: Thank you {name}! "
                f"KES {donation.amount:,.0f} received for {donation.campaign.title}. "
                f"Ref: {donation.kesho_reference}"
            ),
        }

    if 'email' in channels:
        result['email'] = {
            'sent': True,
            'stub': True,
            'to': donation.metadata.get('donor_email') or None,
            'subject': f"ShepherdCare Donation Receipt — {donation.kesho_reference}",
        }

    donation.receipt_sent = True
    donation.save(update_fields=['receipt_sent', 'updated_at'])
    return result