from flask import Blueprint, render_template, request, jsonify, session, redirect, Response
import csv, hmac, io, os, re
from datetime import datetime, date, timedelta
from other.cache import cache
from other.mysql_ import SQL

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "parking.json")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _paging(default_limit=5):
    try: page = max(1, int(request.args.get("page", 1)))
    except ValueError: page = 1
    try: limit = min(100, max(1, int(request.args.get("limit", default_limit))))
    except ValueError: limit = default_limit
    return page, limit, (page - 1) * limit


def _ser(rows):
    return [
        [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in r]
        for r in (rows or [])
    ]


def _scan_filters():
    """Read and validate the guard-history filters from the query string.
    Raises ValueError on a bad date."""
    a = request.args
    f = {}
    guard = (a.get("guard") or "").strip()
    if guard.isdigit():
        f["guard_id"] = int(guard)
    status = (a.get("status") or "").strip().lower()
    if status in ("accepted", "failed", "expired"):
        f["status"] = status
    action = (a.get("action") or "").strip().lower()
    if action in ("entry", "exit"):
        f["action"] = action
    auth = (a.get("auth") or "").strip()
    if auth in ("0", "1"):
        f["authorized"] = int(auth)
    for key in ("date_from", "date_to"):
        value = (a.get(key) or "").strip()
        if value:
            datetime.strptime(value, "%Y-%m-%d")  # ValueError if invalid
            f[key] = value
    if f.get("date_from") and f.get("date_to") and f["date_from"] > f["date_to"]:
        raise ValueError("date range")
    q = (a.get("q") or "").strip()[:50]
    if q:
        f["q"] = q
    return f


def _csv_safe(v):
    """Stop spreadsheet apps from running cell contents as formulas."""
    if v is None:
        return ""
    v = str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


class Admin:
    def __init__(self, sql):
        self.admin = Blueprint("admin", __name__, url_prefix="/admin")
        self.sql: SQL = sql
        self.cache = cache

        self.routes()

    def _protect(self):
        if "user_id" not in session:
            if request.is_json:
                return (
                    jsonify({"status": "unauthenticated", "message": "Please log in"}),
                    401,
                )
            return redirect("/")
        if session.get("role") != "admin":
            return (
                jsonify({"status": "forbidden", "message": "Admin access required"}),
                403,
            )
        # CSRF: browsers can't add a custom header on a cross-site request
        # without a CORS preflight, so requiring one blocks forged writes.
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and request.headers.get("X-Requested-With") != "XMLHttpRequest"
        ):
            return (
                jsonify({"status": "forbidden", "message": "Missing request header"}),
                403,
            )

    def _password_ok(self, password, stored):
        """Check an admin password (bcrypt, with the same plain-text legacy
        fallback the login route uses)."""
        if not password or stored is None:
            return False
        if self.sql._check(password, stored):
            return True
        stored_s = stored.decode() if isinstance(stored, bytes) else str(stored)
        return hmac.compare_digest(password.encode(), stored_s.encode())

    def routes(self):
        self.admin.before_request(self._protect)

        # ─── PAGES ────────────────────────────────────────

        @self.admin.route("/dashboard")
        def dashboard():
            return render_template("admin/dashboard.html")

        @self.admin.route("/park")
        def park():
            return render_template("admin/park.html")

        @self.admin.route("/reports")
        def reports():
            return render_template("admin/reports.html")

        @self.admin.route("/guard_history")
        def guard_history():
            return render_template("admin/guard_history.html")

        @self.admin.route("/users")
        def users():
            return render_template("admin/users.html")

        @self.admin.route("/profile")
        def profile():
            return render_template("admin/profile.html")

        # ─── PARKING ──────────────────────────────────────

        @self.admin.route("/parking", methods=["GET"])
        def parking():
            message = {"status": "failed", "message": "Something went wrong"}
            data = self.sql.getparking()
            if data:
                message.update({"status": "good", "message": "Success", "data": data})
            return jsonify(message)

        @self.admin.route("/setparking", methods=["PUT"])
        def setParking():
            redata = request.get_json(silent=True) or {}
            current = self.sql.getparking()
            try:
                total = int(redata.get("total"))
            except (TypeError, ValueError):
                return jsonify({"status": "bad", "message": "Enter a whole number", "total": current["total"]})
            if total < 1 or total < current["occupied"]:
                return jsonify({"status": "bad", "message": f"Total must be at least {max(1, current['occupied'])} (currently occupied)", "total": current["total"]})
            if not self.sql.setparkingslot(total):
                return jsonify({"status": "bad", "message": "Update Failed", "total": current["total"]})
            return jsonify({"status": "ok", "message": "Updated successfully", "total": total})

        @self.admin.route("/pending_deletions", methods=["GET"])
        def pending_deletions():
            self.sql.purge_expired_deletions()
            self.cache.deletethathas("users")
            rows = self.sql.get_pending_deletions()
            return jsonify({"status": "good", "data": _ser(rows)})

        @self.admin.route("/user_counts")
        def user_counts():
            c = self.sql.countusersbyrole()
            return jsonify({"status": "good", "guard": c.get("guard", 0), "staff": c.get("staff", 0), "user": c.get("user", 0)})

        @self.admin.route("/restore_user/<int:id>", methods=["PUT"])
        def restore_user(id):
            ok = self.sql.restore_user(id)
            self.cache.deletethathas("users")
            if ok:
                return jsonify(
                    {
                        "status": "good",
                        "message": "User account restored. Deletion cancelled.",
                    }
                )
            return jsonify({"status": "bad", "message": "Could not restore user."})

        # ─── USERS ────────────────────────────────────────

        @self.admin.route("/getusers", methods=["GET"])
        def getUsers():
            name = "admin_users"
            page, limit, offset = _paging()

            keyname = f"{name}{limit}_{offset}"
            users = self.cache.get(keyname)
            if users is None:
                users = self.sql.getalluser(limit=limit, offset=offset)
                self.cache.add(keyname, users)
            keyname2 = name + "count"
            total = self.cache.get(keyname2)
            if total is None:
                total = self.sql.countallusers()
                self.cache.add(keyname2, total)

            return jsonify(
                {
                    "status": "good",
                    "data": _ser(users),
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.admin.route("/delete_user/<int:id>", methods=["DELETE"])
        def deleteUser(id):
            self.sql.deleteuser(id)
            self.cache.deletethathas("users")
            return jsonify({"status": "ok", "message": "User deleted successfully"})

        @self.admin.route("/add_user", methods=["POST"])
        def add_user():
            data = request.get_json(silent=True) or {}
            username = (data.get("username") or "").strip()
            email = (data.get("email") or "").strip()
            password = data.get("password") or ""
            role = data.get("role") or ""

            if not all([username, email, password, role]):
                return jsonify({"status": "bad", "message": "All fields are required"})
            if role not in ("guard", "staff"):
                return jsonify({"status": "bad", "message": "Role must be guard or staff"})

            if len(password) < 8:
                return jsonify(
                    {
                        "status": "bad",
                        "message": "Password must be at least 8 characters",
                    }
                )

            if self.sql.getuserbyemail(email):
                return jsonify(
                    {"status": "bad", "message": f"Email '{email}' is already in use"}
                )

            if self.sql.getuserbyusername(username):
                return jsonify(
                    {
                        "status": "bad",
                        "message": f"Username '{username}' is already taken",
                    }
                )

            if not self.sql.adduser(username, email, password, role):
                return jsonify({"status": "bad", "message": "Could not add user"})
            self.cache.deletethathas("users")
            return jsonify({"status": "good", "message": "User added successfully"})

        # ─── QR / REPORTS ─────────────────────────────────

        @self.admin.route("/get_qr", methods=["GET"])
        def getqr():
            name = "admin_qrcode"
            page, limit, offset = _paging()

            keyname = f"{name}{limit}_{offset}"
            if not self.cache.check_key(keyname):
                sqldata = self.sql.getallqr(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)

            data = self.cache.get(keyname)

            keyname2 = name + "qrcount"
            if not self.cache.check_key(keyname2):
                sqltotal = self.sql.countallqr()
                self.cache.add(keyname2, sqltotal)

            total = self.cache.get(keyname2)
            now = datetime.now()

            def qr_status(d):
                status = (d[8] or "active").lower()
                if status == "active" and d[7] and d[7] < now:
                    return "expired"
                return status

            # [code, created_at, created_by, plate, owner, status, valid_until]
            ndata = [
                [str(d[1] or "Pending"), str(d[10]), str(d[14] or "—"),
                 str(d[2] or "—"), str(d[3] or "—"), qr_status(d), str(d[7] or "—")]
                for d in data
            ]

            return jsonify(
                {
                    "status": "good",
                    "data": ndata,
                    "total": total,
                    "page": page,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.admin.route("/recent_users")
        def recent_users():
            page, limit, offset = _paging()
            rows = self.sql.get_recent_users(limit, offset)
            total = self.sql.countallusers()
            # [id, username, role, created_at, status]
            data = [
                [r[0], r[1], r[2], str(r[3]), "pending deletion" if r[4] else "active"]
                for r in rows
            ]
            return jsonify(
                {
                    "status": "good",
                    "data": data,
                    "total": total,
                    "page": page,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.admin.route("/get_entries")
        def entries():
            data = self.sql.get_total_entry_exit()

            keyname = "admin_history_total_scan"
            if not self.cache.check_key(keyname):
                sqlscanned = self.sql.get_total_scan()
                self.cache.add(keyname, sqlscanned)

            scanned = self.cache.get(keyname)
            return jsonify(
                {"entry": data["entry"], "exit": data["exit"], "scan": scanned}
            )

        @self.admin.route("/get_history")
        def gethistory():
            name = "admin_history"
            page, limit, offset = _paging()

            keyname = f"{name}{limit}_{offset}"
            if not self.cache.check_key(keyname):
                sqldata = self.sql.gethistory(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)

            data = self.cache.get(keyname)

            keyname1 = name + "count"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.counthistory()
                self.cache.add(keyname1, sqltotal)

            total = self.cache.get(keyname1)

            return jsonify(
                {
                    "status": "good",
                    "data": _ser(data),
                    "total": total,
                    "page": page,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.admin.route("/get_report_logs")
        def get_report_logs():
            name = "admin_history"
            page, limit, offset = _paging()

            keyname = f"{name}full{limit}_{offset}"
            if not self.cache.check_key(keyname):
                sqldata = self.sql.gethistory_full(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)

            data = self.cache.get(keyname)

            keyname1 = name + "count"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.counthistory()
                self.cache.add(keyname1, sqltotal)
            total = self.cache.get(keyname1)

            return jsonify(
                {
                    "status": "good",
                    "data": _ser(data),
                    "total": total,
                    "page": page,
                    "pages": max(1, -(-total // limit)),
                }
            )

        # ─── GUARD SCAN HISTORY (all guards) ──────────────

        @self.admin.route("/guards")
        def guards():
            rows = self.sql.get_guards()
            return jsonify({"status": "good", "data": [[g[0], g[1]] for g in rows]})

        @self.admin.route("/guard_scans")
        def guard_scans():
            try:
                filters = _scan_filters()
            except ValueError:
                return jsonify({"status": "bad", "message": "Invalid date filter"}), 400
            page, limit, offset = _paging(default_limit=15)
            summary = self.sql.get_scan_summary(filters)
            rows = self.sql.get_scan_history(filters, limit, offset)
            total = summary["total"]
            return jsonify(
                {
                    "status": "good",
                    # [id, date, guard, plate, qr_code, action, result, department, authorized]
                    "data": _ser(rows),
                    "summary": summary,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.admin.route("/guard_scans/export")
        def guard_scans_export():
            try:
                filters = _scan_filters()
            except ValueError:
                return jsonify({"status": "bad", "message": "Invalid date filter"}), 400
            rows = self.sql.get_scan_history(filters, 50000, 0)
            buf = io.StringIO()
            buf.write("\ufeff")  # lets Excel read UTF-8
            w = csv.writer(buf)
            w.writerow(["ID", "Date", "Guard", "Plate", "QR Code", "Action",
                        "Result", "Department", "Authorized"])
            for r in rows:
                r = list(r)
                r[8] = "Yes" if int(r[8] or 0) == 1 else "No"
                w.writerow([_csv_safe(v) for v in r])
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            return Response(
                buf.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename=guard_scan_history_{stamp}.csv"},
            )

        # ─── DASHBOARD ────────────────────────────────────

        @self.admin.route("/dashboard_data")
        def dashboard_data():
            parking = self.sql.getparking()
            entries = self.sql.get_total_entry_exit()
            # Active = status active and not past expiry (revoked, expired and
            # pending-request rows are excluded)
            stats = self.sql.getqrstats()
            active_qr = int(stats[0]) if stats else 0

            return jsonify(
                {
                    "status": "good",
                    "parking_slots": parking.get("total", 0),
                    "occupied": parking.get("occupied", 0),
                    "entered_today": entries["entry"],
                    "active_qr": active_qr,
                }
            )

        @self.admin.route("/activity_chart")
        def activity_chart():
            counts = {str(d): int(c) for d, c in self.sql.get_weekly_entries()}
            today = date.today()
            labels, data = [], []
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                labels.append(d.strftime("%a %d"))
                data.append(counts.get(str(d), 0))
            return jsonify({"status": "good", "labels": labels, "data": data})

        @self.admin.route("/recent_activity")
        def recent_activity():
            rows = self.sql.gethistory_full(limit=10, offset=0)
            result = [{"qr_code": r[4] or "MANUAL", "time": str(r[1]), "action": (r[5] or "entry").lower(), "plate": r[3] or "—", "status": r[6]} for r in rows]
            return jsonify({"status": "good", "data": result})

        # ─── ADMIN PROFILE ────────────────────────────────

        @self.admin.route("/get_profile", methods=["GET"])
        def get_profile():
            row = self.sql.getadminbyid(session["user_id"])
            if not row:
                return jsonify({"status": "bad", "message": "Admin not found"})
            return jsonify({"status": "good", "username": row[0], "email": row[1]})

        @self.admin.route("/update_username", methods=["POST"])
        def update_username():
            data = request.get_json(silent=True) or {}
            username = (data.get("newusername") or "").strip()
            password = data.get("password") or ""

            if len(username) < 3:
                return jsonify({"status": "bad", "message": "Invalid username"})

            # Admins live in the admin table, so check against that, not users.
            stored = self.sql.getadmin_password(session["user_id"])
            if not self._password_ok(password, stored):
                return jsonify({"status": "bad", "message": "Wrong Credentials"})

            if self.sql.admin_username_taken(username, session["user_id"]):
                return jsonify({"status": "bad", "message": "Username is already taken"})

            if self.sql.updateadmin_username(session["user_id"], username):
                return jsonify({"status": "good", "message": "Username updated successfully"})

            return jsonify({"status": "bad", "message": "Something went wrong please try again"})

        @self.admin.route("/update_email", methods=["PUT"])
        def update_email():
            data = request.get_json(silent=True) or {}
            email = (data.get("email") or "").strip().lower()
            password = data.get("password") or ""

            if not email:
                return jsonify({"status": "bad", "message": "Email is required"})
            if not EMAIL_RE.match(email):
                return jsonify(
                    {"status": "bad", "message": "Enter a valid email address"}
                )

            stored = self.sql.getadmin_password(session["user_id"])
            if not self._password_ok(password, stored):
                return jsonify({"status": "bad", "message": "Wrong Credentials"})

            if self.sql.admin_email_taken(email, session["user_id"]):
                return jsonify({"status": "bad", "message": "Email is already in use"})

            if not self.sql.updateadmin_email(session["user_id"], email):
                return jsonify({"status": "bad", "message": "Failed to update email"})
            session["email"] = email
            return jsonify({"status": "good", "message": "Email updated successfully"})

        @self.admin.route("/update_password", methods=["PUT"])
        def update_password():
            data = request.get_json(silent=True) or {}
            current_pw = data.get("current_password", "")
            new_pw = data.get("new_password", "")
            confirm_pw = data.get("confirm_password", "")

            if not all([current_pw, new_pw, confirm_pw]):
                return jsonify(
                    {"status": "bad", "message": "All password fields are required"}
                )

            if len(new_pw) < 8:
                return jsonify(
                    {
                        "status": "bad",
                        "message": "New password must be at least 8 characters",
                    }
                )

            if new_pw != confirm_pw:
                return jsonify(
                    {"status": "bad", "message": "New passwords do not match"}
                )

            stored = self.sql.getadmin_password(session["user_id"])
            if stored is None:
                return jsonify({"status": "bad", "message": "Admin not found"})

            if not self._password_ok(current_pw, stored):
                return jsonify(
                    {"status": "bad", "message": "Current password is incorrect"}
                )

            if not self.sql.updateadmin_password(session["user_id"], new_pw):
                return jsonify(
                    {"status": "bad", "message": "Failed to update password"}
                )

            return jsonify(
                {"status": "good", "message": "Password updated successfully"}
            )