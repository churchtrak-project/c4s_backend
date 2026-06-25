"""
Populate demo data for the Pastoral Wellness Fund (wellnessfund frontend).

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --flush   # delete demo church data first
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from churches.models import Church, Pastor
from fundraising.models import Campaign, CampaignUpdate, Donation, Disbursement

DEMO_CHURCH_SLUG = 'nairobi-shepherds-church'
DEMO_CAMPAIGN_UUID = uuid.UUID('11111111-1111-1111-1111-111111111111')

ACCOUNTS = [
    {
        'role': User.ROLE_CFS_SUPERADMIN,
        'email': 'cfs@shepherdcare.co.ke',
        'phone': '+254700000001',
        'password': 'cfs123',
        'full_name': 'Dr. Esther Kamau',
        'church': None,
    },
    {
        'role': User.ROLE_CFS_STAFF,
        'email': 'staff@shepherdcare.co.ke',
        'phone': '+254700000002',
        'password': 'staff123',
        'full_name': 'Grace Wanjiku',
        'church': None,
    },
    {
        'role': User.ROLE_COUNSELOR,
        'email': 'counselor@shepherdcare.co.ke',
        'phone': '+254700000003',
        'password': 'counselor123',
        'full_name': 'Dr. Ruth Achieng',
        'church': None,
    },
    {
        'role': User.ROLE_CHURCH_ADMIN,
        'email': 'admin@nsc.org',
        'phone': '+254712000001',
        'password': 'admin123',
        'full_name': 'Mary Njoroge',
        'church': 'assign',
    },
    {
        'role': User.ROLE_FINANCE_OFFICER,
        'email': 'deacon@nsc.org',
        'phone': '+254712000002',
        'password': 'deacon123',
        'full_name': 'Deacon Paul Kamau',
        'church': 'assign',
    },
    {
        'role': User.ROLE_PASTOR,
        'email': 'pastor@nsc.org',
        'phone': '+254712000003',
        'password': 'pastor123',
        'full_name': 'Pastor James Kariuki',
        'church': 'assign',
    },
    {
        'role': User.ROLE_MINISTRY_LEADER,
        'email': 'leader@nsc.org',
        'phone': '+254712000004',
        'password': 'leader123',
        'full_name': 'Simon Mwangi',
        'church': 'assign',
    },
    {
        'role': User.ROLE_CHURCH_MEMBER,
        'email': 'member@nsc.org',
        'phone': '+254712000005',
        'password': 'member123',
        'full_name': 'Faith Wanjiru',
        'church': 'assign',
    },
    {
        'role': User.ROLE_DONOR,
        'email': 'donor@nsc.org',
        'phone': '+254712000006',
        'password': 'donor123',
        'full_name': 'John Kamau',
        'church': 'assign',
    },
]


class Command(BaseCommand):
    help = 'Seed demo church, users (all roles), campaign, donations, and disbursements.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Remove existing demo church and related records before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            Church.objects.filter(slug=DEMO_CHURCH_SLUG).delete()
            for spec in ACCOUNTS:
                User.objects.filter(phone=spec['phone']).delete()
            self.stdout.write(self.style.WARNING('Flushed existing demo data.'))

        church, _ = Church.objects.get_or_create(
            slug=DEMO_CHURCH_SLUG,
            defaults={
                'name': "Nairobi Shepherd's Church",
                'county': 'Nairobi',
                'contact_phone': '+254712000000',
                'contact_email': 'office@nsc.org',
                'member_count': 240,
                'wellness_avg': 72,
            },
        )

        pastor, _ = Pastor.objects.get_or_create(
            church=church,
            defaults={
                'full_name': 'Pastor James Kariuki',
                'phone': '+254712000003',
                'email': 'pastor@nsc.org',
                'wellness_score': 68,
                'years_of_service': 14,
                'last_rest_date': date.today() - timedelta(days=45),
                'status': Pastor.STATUS_STABLE,
            },
        )

        users_by_role = {}
        for spec in ACCOUNTS:
            church_fk = church if spec['church'] == 'assign' else None
            user, created = User.objects.get_or_create(
                phone=spec['phone'],
                defaults={
                    'email': spec['email'],
                    'full_name': spec['full_name'],
                    'role': spec['role'],
                    'church': church_fk,
                },
            )
            if not created:
                user.email = spec['email']
                user.full_name = spec['full_name']
                user.role = spec['role']
                user.church = church_fk
                user.save()
            user.set_password(spec['password'])
            user.save()
            users_by_role[spec['role']] = user
            self.stdout.write(f"  {'Created' if created else 'Updated'} {spec['role']}: {spec['email']}")

        pastor.user = users_by_role.get(User.ROLE_PASTOR)
        pastor.save(update_fields=['user'])

        admin = users_by_role[User.ROLE_CHURCH_ADMIN]
        campaign, created = Campaign.objects.get_or_create(
            public_uuid=DEMO_CAMPAIGN_UUID,
            defaults={
                'church': church,
                'pastor': pastor,
                'title': 'Sabbatical & Family Retreat Fund 2025',
                'description': (
                    "Pastor James has served our congregation faithfully for 14 years — "
                    "through grief, joy, pandemic, and growth — without ever taking a sabbatical. "
                    "This fund will send Pastor James and his family on a fully-funded 7-day retreat "
                    "at the Great Rift Valley Lodge in Naivasha."
                ),
                'goal_amount': Decimal('120000'),
                'start_date': date(2025, 6, 14),
                'end_date': date(2025, 8, 6),
                'created_by': admin,
                'is_active': True,
            },
        )
        self.stdout.write(f"  Campaign: {campaign.title} (uuid={campaign.public_uuid})")

        Campaign.objects.get_or_create(
            church=church,
            pastor=pastor,
            title='Monthly Day Away Fund — 2025',
            defaults={
                'description': 'Recurring fund for one structured rest day per month throughout 2025.',
                'goal_amount': Decimal('54000'),
                'start_date': date(2025, 1, 1),
                'end_date': date(2025, 12, 31),
                'created_by': admin,
                'is_active': True,
            },
        )

        updates = [
            ('Mary Njoroge (Church Admin)', 'Campaign launched. 12 donors in the first 24 hours. God is faithful!'),
            ('Deacon Paul Kamau', 'The Accountability Board has approved the retreat booking at Great Rift Valley Lodge. Dates confirmed: Aug 14–21.'),
            ('Mary Njoroge (Church Admin)', 'We crossed 70%! Thank you to everyone who has given. Only KES 35,500 to go. Share with three friends today.'),
        ]
        for author_name, text in updates:
            CampaignUpdate.objects.get_or_create(
                campaign=campaign,
                author_name=author_name,
                text=text,
            )

        donation_specs = [
            ('+254712345678', 'John K.', Decimal('5000'), False, 2),
            ('+254722456789', '', Decimal('10000'), True, 5),
            ('+254733567890', 'Faith W.', Decimal('2000'), False, 24),
            ('+254744678901', 'David O.', Decimal('3500'), False, 26),
            ('+254755789012', 'Grace A.', Decimal('1500'), False, 48),
            ('+254766890123', '', Decimal('7000'), True, 50),
            ('+254777901234', 'Peter N.', Decimal('500'), False, 72),
            ('+254788012345', 'Sarah M.', Decimal('8500'), False, 3),
        ]
        for i, (phone, name, amount, anon, hours_ago) in enumerate(donation_specs):
            ref = f'SCF-{campaign.id:02d}{i:02d}AB'
            Donation.objects.get_or_create(
                kesho_reference=ref,
                defaults={
                    'church': church,
                    'campaign': campaign,
                    'donor_phone': phone,
                    'donor_name': name,
                    'is_anonymous': anon,
                    'amount': amount,
                    'status': Donation.STATUS_SUCCESS,
                    'payment_method': 'M-Pesa',
                    'receipt_sent': True,
                    'received_at': timezone.now() - timedelta(hours=hours_ago),
                },
            )

        finance = users_by_role[User.ROLE_FINANCE_OFFICER]
        Disbursement.objects.get_or_create(
            reference='DSB-002',
            defaults={
                'church': church,
                'campaign': campaign,
                'amount': Decimal('12000'),
                'purpose': 'Dr. Ruth Achieng Counseling ×4 sessions',
                'category': 'Counseling',
                'intended_date': date(2025, 7, 10),
                'requested_by': admin,
                'approved_by': finance,
                'status': Disbursement.STATUS_PAID,
                'payout_phone': '+254700000003',
                'proof_notes': 'Invoice #RC-2025-044 attached',
                'approved_at': timezone.now() - timedelta(days=14),
                'paid_at': timezone.now() - timedelta(days=13),
            },
        )
        Disbursement.objects.get_or_create(
            reference='DSB-003',
            defaults={
                'church': church,
                'campaign': campaign,
                'amount': Decimal('4500'),
                'purpose': 'Day Away — June Wellness Day',
                'category': 'Day Away',
                'intended_date': date(2025, 6, 28),
                'requested_by': admin,
                'approved_by': finance,
                'status': Disbursement.STATUS_PAID,
                'payout_phone': '+254712000003',
                'proof_notes': 'Trademark Hotel Karen receipt',
                'approved_at': timezone.now() - timedelta(days=26),
                'paid_at': timezone.now() - timedelta(days=25),
            },
        )
        Disbursement.objects.get_or_create(
            reference='DSB-001',
            defaults={
                'church': church,
                'campaign': campaign,
                'amount': Decimal('45000'),
                'purpose': 'Great Rift Valley Lodge — 7 nights family accommodation',
                'category': 'Retreat Accommodation',
                'intended_date': date(2025, 8, 14),
                'requested_by': admin,
                'status': Disbursement.STATUS_REQUESTED,
                'payout_phone': '+254712000003',
                'proof_notes': 'Booking confirmation attached. Non-refundable rate secured.',
                'notes': 'Payment due by Aug 1.',
            },
        )

        raised = campaign.total_raised
        disbursed = campaign.total_disbursed
        church.current_fund_balance = raised - disbursed
        church.save(update_fields=['current_fund_balance'])

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo seed complete.\n"
            f"  Church: {church.name}\n"
            f"  Campaign UUID: {campaign.public_uuid}\n"
            f"  Raised: KES {raised:,.0f} | Balance: KES {campaign.current_balance:,.0f}\n"
            f"  Credentials: see DEMO_CREDENTIALS.md\n"
        ))