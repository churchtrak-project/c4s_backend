# Demo Account Credentials

These accounts are created by `python manage.py seed_demo`. All are for **local development only**.

**API base (local):** `http://localhost:8000/api/`

**Login:** `POST /api/auth/login/` with JSON body `{ "email": "...", "password": "..." }`  
(or use `"identifier"` instead of `"email"`). Response includes `token` and `user` profile.

**Auth header for protected routes:** `Authorization: Token <token>`

---

## Primary wellnessfund demo accounts (match the frontend UI)

| Role | Label | Email | Password | Phone |
|------|-------|-------|----------|-------|
| Church Admin | Mary Njoroge | `admin@nsc.org` | `admin123` | +254712000001 |
| Accountability Officer (finance_officer) | Deacon Paul Kamau | `deacon@nsc.org` | `deacon123` | +254712000002 |
| CFS Super Admin | Dr. Esther Kamau | `cfs@shepherdcare.co.ke` | `cfs123` | +254700000001 |

---

## All seeded roles

| Role | Name | Email | Password | Scope |
|------|------|-------|----------|-------|
| `cfs_superadmin` | Dr. Esther Kamau | cfs@shepherdcare.co.ke | cfs123 | Global |
| `cfs_staff` | Grace Wanjiku | staff@shepherdcare.co.ke | staff123 | Global |
| `counselor` | Dr. Ruth Achieng | counselor@shepherdcare.co.ke | counselor123 | Global |
| `church_admin` | Mary Njoroge | admin@nsc.org | admin123 | Nairobi Shepherd's Church |
| `finance_officer` | Deacon Paul Kamau | deacon@nsc.org | deacon123 | Nairobi Shepherd's Church |
| `pastor` | Pastor James Kariuki | pastor@nsc.org | pastor123 | Nairobi Shepherd's Church |
| `ministry_leader` | Simon Mwangi | leader@nsc.org | leader123 | Nairobi Shepherd's Church |
| `church_member` | Faith Wanjiru | member@nsc.org | member123 | Nairobi Shepherd's Church |
| `donor` | John Kamau | donor@nsc.org | donor123 | Nairobi Shepherd's Church |

---

## Demo campaign (public, no login)

| Field | Value |
|-------|-------|
| Church | Nairobi Shepherd's Church |
| Pastor | Pastor James Kariuki |
| Title | Sabbatical & Family Retreat Fund 2025 |
| Public UUID | `11111111-1111-1111-1111-111111111111` |
| Public API | `GET /api/public/campaigns/11111111-1111-1111-1111-111111111111/` |
| Ledger API | `GET /api/public/campaigns/11111111-1111-1111-1111-111111111111/ledger/` |

---

## Key API endpoints

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/auth/login/` | No | Returns token + user |
| GET | `/api/auth/me/` | Token | Current user profile |
| GET | `/api/dashboard/` | Token | Church fund overview |
| GET/POST | `/api/campaigns/` | Token (write: church_admin, CFS) | Campaign CRUD |
| GET | `/api/donations/` | Token (fund staff) | Receipts list |
| POST | `/api/donations/<id>/resend-receipt/` | Token | SMS/email stub |
| GET/POST | `/api/disbursements/` | Token | Create: church_admin; approve: finance_officer |
| POST | `/api/disbursements/<id>/approve/` | Token (finance_officer, CFS) | Second signature |
| POST | `/api/disbursements/<id>/reject/` | Token (finance_officer, CFS) | Reject request |
| POST | `/api/donate/` | No | **Returns 502** — KeshoPay not configured |

---

## Reseed

```bash
python manage.py seed_demo --flush
python manage.py seed_demo
```