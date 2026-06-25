# careforsheperds

**Phase 1 Backend** — Care for Shepherds (Pastoral Wellness Fund + Fundraising)

Simple Django + DRF backend focused exclusively on the Fundraising & Pastoral Wellness Fund module.

## Tech
- Django 5 + DRF
- PostgreSQL (required)
- KeshoPay integration (single merchant account — attribution via reference + metadata)
- Django Admin + DRF APIs (both supported from day one)

## Project Structure (kept deliberately simple)
```
careforsheperds/          # Django project package
accounts/                 # Custom User (phone-based) + roles + ChurchSignup
churches/                 # Church (tenant) + Pastor (1 per church)
fundraising/              # Campaign, Pledge (recurring), Donation, Disbursement + business logic
payments/                 # KeshoPay service + webhook + audit Transaction
```

## Quick Start

### 1. Environment
```bash
cd /home/ngigi/Documents/ignite
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values (especially DATABASE_URL and KeshoPay keys)
```

### 2. PostgreSQL (required)
Create the database and role (example using psql or Docker):

**Docker (recommended for dev):**
```bash
docker run --name cfs-postgres -e POSTGRES_PASSWORD=careforsheperds -e POSTGRES_USER=careforsheperds -e POSTGRES_DB=careforsheperds -p 5432:5432 -d postgres:16
```

Then in `.env`:
```
DATABASE_URL=postgres://careforsheperds:careforsheperds@localhost:5432/careforsheperds
```

### 3. Migrations & Superuser (CFS Super Admin)
```bash
python manage.py migrate
python manage.py createsuperuser --phone 254700000000   # or whatever phone you want for the CFS superadmin
```

The superuser will be created with role `cfs_superadmin` (global, no church).

### 4. Run
```bash
python manage.py runserver
```

### 5. Key Endpoints

**Public / Guest (no auth)**
- `POST /api/auth/church-signup/` — Self-signup flow (creates Church + ChurchAdmin + Pastor + optional starter Campaign)
- `GET /api/public/campaigns/<uuid>/` — Public campaign page data (thermometer etc.)
- `POST /api/donate/` — Guest M-Pesa donation (phone + amount + campaign_public_uuid). Returns checkout info from KeshoPay.
- `GET /api/campaigns/<id>/ledger/` — Transparent public-ish ledger

**Authenticated (DRF or Django Admin login)**
- Full CRUD on campaigns etc. (tenant-scoped)
- Admin at `/admin/`

**Payments**
- `POST /api/payments/webhook/keshopay/` — The webhook KeshoPay must call (returns 200 always)
- Helper initiate at `/api/payments/initiate/`

## KeshoPay Integration Notes
- Uses **one merchant account** (keys in `.env`).
- Every payment carries `reference` (e.g. `CFS-CAMP-7-abc123`) + `metadata` containing `church_id`, `campaign_id`, etc.
- Authorization key is generated **server-side only** (see `payments/services.py`).
- Webhook updates `Donation.status` and creates `PaymentTransaction` audit row.
- **Action required**: Email support@keshopay.co.ke for sandbox keys + exact base URL + webhook registration + test phone numbers.

## Recurring Giving (basic v1 model)
- `Pledge` model exists with frequency + status + next_due_date.
- `Donation` has nullable FK `pledge`.
- Actual money still arrives as individual Donation records via M-Pesa.

## Next (after Phase 1 is solid)
- Real frontend (campaign pages, donor flow) — frontend now exists; backend extended to provide matching endpoints
- Proper authentication (now has /api/auth/login/ returning token + role profile)
- Disbursement payout calls to KeshoPay
- Better pledge fulfillment reminders

## Expanded API Surface (to power full frontend)
**Auth**
- POST /api/auth/login/ — identifier (email/phone) + password → {token, user:{id,name,email,role,church,initials}}

**Core tenant & oversight (CFS + scoped)**
- /api/churches/ , /api/pastors/ (CRUD + search/status filters; CFS global, others scoped)
- /api/stats/ — platform aggregates for dashboards (CFS only)

**Church operations**
- /api/members/ (CRUD, cell/ministry/attendance filters)
- /api/events/ (CFS + church events, registrations count)
- /api/tasks/ (assignable tasks per role/church)
- /api/resources/ (content, sermons, library)
- /api/assessments/ (pastor wellness self-assessments + history)

**Counseling**
- /api/counseling/counselors/ , /api/counseling/cases/ , /api/counseling/sessions/

**Fundraising (Phase 1, still primary)**
- /api/campaigns/ , /api/donate/ , /api/public/campaigns/<uuid>/ , /api/campaigns/<id>/ledger/ , disbursements via model

All endpoints are tenant-aware and role-permissioned. Use Token auth header after login.

## Important
- All financial data is strictly per-Church (multi-tenant via FK + queryset filtering).
- One primary Pastor per Church.
- Purely guest donations (phone number only).

Built following the CARE FOR SHEPHERDS SRS v2.0 — Phase 1 only.
