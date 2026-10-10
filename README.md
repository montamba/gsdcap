# GSD Parking System 🚗

A lightweight, web-based vehicle parking monitoring system powered by Flask and MySQL. Staff issue QR passes, guards scan them at the gate, and admins manage everything else.

---

## 🚀 Tech Stack
* **Backend:** Python / Flask, MySQL
* **Frontend:** HTML, CSS, JavaScript, Bootstrap Icons, Chart.js, `html5-qrcode`, `qrcodejs`
* **Security & Utils:** `bcrypt`, `qrcode` (Python), python-dotenv

---

## 👥 Roles & Access
* **Admin (`/`):** Manage parking capacity, staff/guard accounts, reports, and pending account deletions.
* **Staff (`/`):** Generate, renew, revoke, and email QR codes; review user pass requests.
* **Guard (`/`):** Scan QR codes for entry/exit, log manual vehicle entries, view live parking map.
* **User (`/user/signin`):** Sign up, request/renew QR passes, and check pass status.

---

## ⚙️ Quick Setup

### 1. Install dependencies
```bash
pip install flask mysql-connector-python bcrypt "qrcode[pil]" python-dotenv