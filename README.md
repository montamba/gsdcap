# GSD Parking System

A web-based vehicle parking monitoring system. Staff issue QR passes for vehicles, guards scan them at the gate to log entry and exit, and admins manage users, parking capacity, and reports.

**Stack:** Flask (Python) · MySQL · HTML/CSS/JavaScript · Bootstrap Icons · Chart.js · html5-qrcode · qrcodejs

---

## Features

### Roles

| Role | Login | What they can do |
|------|-------|------------------|
| **Admin** | `/` (Admin tab) | Dashboard, set total parking slots, manage staff/guard accounts, restore or delete pending account deletions, view reports and logs |
| **Staff** | `/` (Staff tab) | Generate, preview, save, and email QR codes; search, renew, and revoke QR codes; review user QR/renewal requests; view history |
| **Guard** | `/` (Guard tab) | Scan QR codes for entry/exit, manual entry for vehicles without a QR, view live parking map, view own scan history |
| **User** | `/user/signin` | Sign up, request a new QR pass, view own QR codes, request renewal, manage profile |

### Core flow

1. A **user** requests a QR pass, or **staff** create one directly.
2. Staff approve the request, which generates a unique code (`GSD-XXXXX-XXXXX`).
3. The code is emailed to the owner as a QR image.
4. A **guard** scans the QR and selects ENTRY or EXIT. The system checks:
   - the QR exists and is not revoked
   - the QR has not expired
   - the vehicle is not already in or out
   - there is free space (entry only)
5. Every scan is logged in `history` (accepted, failed, or expired), and parking counts update.

### Parking capacity

- A **car uses 2 units** and a **motorcycle uses 1 unit**, so a motorcycle takes half a slot.
- `parking.total_occupied` stores fractional slot usage. `parking.occupied` is that value rounded up.

### Account deletion

Staff and guards can request deletion from their profile. The request is flagged for the admin, who can restore the account within **30 days**. After that the account is eligible for permanent deletion (`purge_expired_deletions`).

---

## Project structure

```
app.py                  Flask app, login/logout/signup, blueprint registration
other/
  admin.py              /admin/*  blueprint
  staff.py              /staff/*  blueprint
  guard.py              /guard/*  blueprint
  users.py              /users/*  blueprint
  mysql_.py             SQL class: all database queries, email, QR image generation
  cache.py              In-memory cache, auto-cleared every 60 seconds
static/
  css/                  style.css (admin/user), staff.css, message.css
  scripts/scrit.js      API wrapper, message modal, escapeHTML helper
templates/
  index.html            Admin / staff / guard login
  development.html      "Under development" placeholder page
  admin/                dashboard, park, users, reports, profile
  staff/                generate, history, search, profile, userrequest
  guard/                scanner, history, parking, profile
  users/                usersignin, userssigup, userqr, userprofile
kkkk.sql                Database dump (schema + sample data)
```

---

## Setup

### 1. Requirements

- Python 3.10+
- MySQL 8

```bash
pip install flask mysql-connector-python bcrypt "qrcode[pil]" python-dotenv
```

### 2. Database

```bash
mysql -u <user> -p -e "CREATE DATABASE gsdparking;"
mysql -u <user> -p gsdparking < kkkk.sql
```

Tables: `admin`, `users`, `qrcode`, `qrpending`, `history`, `parking`, `request_history`.

> The sample dump contains test accounts and a plaintext admin password. **Do not use it in production.** Create your own admin with a bcrypt-hashed password and remove the sample data.

### 3. Environment variables

Create a `.env` file in the project root:

```env
# Database
USER=your_mysql_user
PASSW=your_mysql_password
LOCALHOST=127.0.0.1
DATABASE=gsdparking
MYSQLPORT=3306

# Flask
SECRET_KEY=change-me-to-a-long-random-string

# Email (for sending QR codes)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

For Gmail, use an **App Password**, not your normal password.

### 4. Run

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

For production, run without `debug=True` behind a WSGI server such as gunicorn.

---

## Main routes

### Pages

| URL | Role |
|-----|------|
| `/` | Login (admin, staff, guard) |
| `/user/signin`, `/user/signuppage` | User login and signup |
| `/admin/dashboard`, `/admin/park`, `/admin/users`, `/admin/reports`, `/admin/profile` | Admin |
| `/staff/generate`, `/staff/history`, `/staff/search`, `/staff/profile`, `/staff/userreques` | Staff |
| `/guard/scan`, `/guard/history`, `/guard/parking`, `/guard/profile` | Guard |
| `/users/status`, `/users/profile` | User |

### Key API endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /auth/login` | Log in with email, password, and role |
| `POST /guard/check_qr` | Validate a scanned QR and log entry/exit |
| `POST /guard/manual_entry` | Log a vehicle without a QR |
| `GET /guard/getParking` | Current parking totals |
| `POST /staff/save_qr` | Save a new QR code |
| `PUT /staff/renew_qr/<id>` | Set a new expiry on a QR |
| `PUT /staff/revoke_qr` | Revoke a QR (frees the slot if the vehicle was inside) |
| `POST /staff/send_qr_email` | Email the QR image to the owner |
| `PUT /staff/approve_request/<id>` | Approve a user's QR request |
| `PUT /staff/approve_renewal/<id>` | Approve a renewal with a new expiry |
| `PUT /admin/setparking` | Set total parking slots |
| `GET /admin/getusers`, `POST /admin/add_user`, `DELETE /admin/delete_user/<id>` | User management |
| `GET /admin/pending_deletions`, `PUT /admin/restore_user/<id>` | Deletion requests |

List endpoints take `?page=` and `?limit=` and return `status`, `data`, `total`, `page`, `pages`.

---

## How it works

- **Auth:** session-based (Flask sessions). Passwords are hashed with bcrypt. Each blueprint has a `before_request` guard that checks the session role.
- **Frontend:** each page fetches JSON through the `API` helper in `scrit.js`. Messages appear in a shared modal (`showMessageModal`).
- **Caching:** list queries are cached in memory for up to 60 seconds. Writes call `cache.deletethathas("<keyword>")` to invalidate related keys.
- **QR codes:** only the code string is stored in the database. The QR image is generated in the browser (qrcodejs) for display and printing, and server-side (`qrcode` library) for email.

---

## Known issues

Found during a code review. See the review notes for details and fixes.

- Reports & Logs query references a non-existent `users.plate` column.
- `getparking()` reads `total_occupied` from the wrong column index.
- Logged-in guards and users can hit a redirect loop on `/`.
- The shared MySQL connection is not thread-safe.
- Several list pages filter or count only the current page.
- Account-deletion lock and 30-day purge are not enforced in code.

---

## Security notes

- Set a strong `SECRET_KEY` and never commit `.env` or `kkkk.sql` with real data.
- Replace plaintext admin passwords with bcrypt hashes.
- Turn off `debug=True` in production.