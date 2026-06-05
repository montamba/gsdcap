from flask import Blueprint, render_template, request, jsonify, session, redirect
import json, os
from other.cache import cache

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "parking.json")


class Admin:
    def __init__(self, sql):
        self.admin = Blueprint("admin", __name__, url_prefix="/admin")
        self.sql = sql
        self.cache = cache
        
        
        self.routes()

    def _protect(self):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"status": "unauthenticated", "message": "Please log in"}), 401
            return redirect("/")
        if session.get("role") != "admin":
            return jsonify({"status": "forbidden", "message": "Admin access required"}), 403

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
            with open(file_path, "r") as file:
                data = json.load(file)
            if data:
                message.update({"status": "good", "message": "Success", "data": data})
            return jsonify(message)

        @self.admin.route("/setparking", methods=["PUT"])
        def setParking():
            redata = request.get_json()
            total = int(redata.get("total", 0))
            with open(file_path, "r") as file:
                jdata = json.load(file)
            jdata["total"] = total
            jdata["available"] = total - jdata["occupied"]
            with open(file_path, "w") as file:
                json.dump(jdata, file, indent=4)
            return jsonify({"status": "ok", "message": "Updated successfully", "total": total})
        
        @self.admin.route("/pending_deletions", methods=["GET"])
        def pending_deletions():
            rows = self.sql.get_pending_deletions()
            serialized = [
                [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in r]
                for r in rows
            ]
            return jsonify({"status": "good", "data": serialized})
 
        @self.admin.route("/restore_user/<int:id>", methods=["PUT"])
        def restore_user(id):
            ok = self.sql.restore_user(id)
            self.cache.deletethathas("users")
            if ok:
                return jsonify({"status": "good", "message": "User account restored. Deletion cancelled."})
            return jsonify({"status": "bad", "message": "Could not restore user."})

        # ─── USERS ────────────────────────────────────────
        

        @self.admin.route("/getusers", methods=["GET"])
        def getUsers():
            name = "admin_users"
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            keyname = name + str(offset)
            if not self.cache.check_key(keyname):
                sqlusers = self.sql.getalluser(limit=limit, offset=offset)
                self.cache.add(keyname, sqlusers)
                
                
            users = self.cache.get(keyname)
            
            keyname2 = name + "count"
            if not self.cache.check_key(keyname2):
                sqltotal = self.sql.countallusers()
                self.cache.add(keyname2, sqltotal)
                
            total = self.cache.get(keyname2)

            serialized = [
                [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in u]
                for u in users
            ]
            return jsonify({
                "status": "good",
                "data":   serialized,
                "total":  total,
                "page":   page,
                "limit":  limit,
                "pages":  max(1, -(-total // limit))
            })

        @self.admin.route("/delete_user/<int:id>", methods=["DELETE"])
        def deleteUser(id):
            self.sql.deleteuser(id)
            self.cache.deletethathas("users")
            return jsonify({"status": "ok", "message": "User deleted successfully"})

        @self.admin.route("/add_user", methods=["POST"])
        def add_user():
            data = request.get_json()
            username = data.get("username", "").strip()
            email    = data.get("email", "").strip()
            password = data.get("password", "")
            role     = data.get("role", "")

            if not all([username, email, password, role]):
                return jsonify({"status": "bad", "message": "All fields are required"})

            if len(password) < 8:
                return jsonify({"status": "bad", "message": "Password must be at least 8 characters"})

            if self.sql.getuserbyemail(email):
                return jsonify({"status": "bad", "message": f"Email '{email}' is already in use"})

            if self.sql.getuserbyusername(username):
                return jsonify({"status": "bad", "message": f"Username '{username}' is already taken"})

            self.sql.adduser(username, email, password, role)
            self.cache.deletethathas("users")
            return jsonify({"status": "good", "message": "User added successfully"})

        # ─── QR / REPORTS ─────────────────────────────────

        @self.admin.route("/get_qr", methods=["GET"])
        def getqr():
            name = "admin_qrcode"
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            keyname = name + str(offset)
            if not self.cache.check_key(keyname):
                sqldata  = self.sql.getallqr(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)
            
            data = self.cache.get(keyname)
            
            keyname2 = name + "qrcount"
            if not self.cache.check_key(keyname2):
                sqltotal = self.sql.countallqr()
                self.cache.add(keyname2, sqltotal)
                
            total = self.cache.get(keyname2)
            ndata = [[str(d[1]), str(d[8]), str(d[10] or "—")] for d in data]

            return jsonify({
                "status": "good",
                "data":   ndata,
                "total":  total,
                "page":   page,
                "pages":  max(1, -(-total // limit))
            })

        @self.admin.route("/get_entries")
        def entries():
            data = self.sql.get_total_entry_exit()
            
            keyname = "admin_history_total_scan"
            if not self.cache.check_key(keyname):
                sqlscanned = self.sql.get_total_scan()
                self.cache.add(keyname, sqlscanned)
                
            scanned = self.cache.get(keyname)
            return jsonify({
                "entry": data["entry"],
                "exit":  data["exit"],
                "scan":  scanned
            })

        @self.admin.route("/get_history")
        def gethistory():
            name = "admin_history"
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            keyname = name + str(offset)
            if not self.cache.check_key(keyname):
                sqldata = self.sql.gethistory(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)
                
            data = self.cache.get(keyname)
            
            keyname1 = name + "count"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.counthistory()
                self.cache.add(keyname1, sqltotal)
                
            total = self.cache.get(keyname1)

            serialized = [
                [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in row]
                for row in data
            ]
            return jsonify({
                "status": "good",
                "data":   serialized,
                "total":  total,
                "page":   page,
                "pages":  max(1, -(-total // limit))
            })

        @self.admin.route("/get_report_logs")
        def get_report_logs():
            name = "admin_history"
            page   = max(1, int(request.args.get("page", 1)))
            limit  = int(request.args.get("limit", 5))
            offset = (page - 1) * limit
            
            keyname = name + "full" + str(offset)
            if not self.cache.check_key(keyname):
                sqldata  = self.sql.gethistory_full(limit=limit, offset=offset)
                self.cache.add(keyname, sqldata)
                
            data = self.cache.get(keyname)

            keyname1 = name + "count"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.counthistory()
                self.cache.add(keyname1, sqltotal)
            total = self.cache.get(keyname1)

            serialized = [
                [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in row]
                for row in data
            ]
            return jsonify({
                "status": "good",
                "data":   serialized,
                "total":  total,
                "page":   page,
                "pages":  max(1, -(-total // limit))
            })

        # ─── DASHBOARD ────────────────────────────────────

        @self.admin.route("/dashboard_data")
        def dashboard_data():
            name = "admin_qrcode"
            parking  = self.sql.getparking()
            entries  = self.sql.get_total_entry_exit()
            
            keyname = name + "qrcount"
            if not self.cache.check_key(keyname):
                sqlactive_qr = self.sql.countallqr()
                self.cache.add(keyname, sqlactive_qr)
                
            active_qr = self.cache.get(keyname)
            
            return jsonify({
                "status":        "good",
                "parking_slots": parking.get("total", 0),
                "occupied":      parking.get("occupied", 0),
                "entered_today": entries["entry"],
                "active_qr":     active_qr
            })

        @self.admin.route("/activity_chart")
        def activity_chart():
            return jsonify({"status": "good", "labels": [], "data": []})

        @self.admin.route("/recent_activity")
        def recent_activity():
            name = "admin_qrcode"
            
            keyname = name + str(0)
            if not self.cache.check_key(keyname):
                sqlrows  = self.sql.getallqr(limit=10, offset=0)
                self.cache.add(keyname, sqlrows)
            
            rows = self.cache.get(keyname)
            
            result = []
            for r in rows:
                result.append({
                    "qr_code": r[1],
                    "time": str(r[8]),
                    "action":"entry" if r[9] == "IN" else "exit",
                    "plate": r[2] or "—",
                    "status": "accepted"
                })
            return jsonify({"status": "good", "data": result})

        # ─── ADMIN PROFILE ────────────────────────────────

        @self.admin.route("/get_profile", methods=["GET"])
        def get_profile():
            row = self.sql.getadminbyid(session["user_id"])
            if not row:
                return jsonify({"status": "bad", "message": "Admin not found"})
            return jsonify({
                "status":   "good",
                "username": row[0],
                "email":    row[1]
            })

        @self.admin.route("/update_email", methods=["PUT"])
        def update_email():
            data  = request.get_json()
            email = (data.get("email") or "").strip()

            if not email:
                return jsonify({"status": "bad", "message": "Email is required"})
            if "@" not in email:
                return jsonify({"status": "bad", "message": "Enter a valid email address"})

            try:
                self.sql.updateadmin_email(session["user_id"], email)
                session["email"] = email
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "Failed to update email"})

            return jsonify({"status": "good", "message": "Email updated successfully"})

        @self.admin.route("/update_password", methods=["PUT"])
        def update_password():
            data         = request.get_json()
            current_pw   = data.get("current_password", "")
            new_pw       = data.get("new_password", "")
            confirm_pw   = data.get("confirm_password", "")

            if not all([current_pw, new_pw, confirm_pw]):
                return jsonify({"status": "bad", "message": "All password fields are required"})

            if len(new_pw) < 8:
                return jsonify({"status": "bad", "message": "New password must be at least 8 characters"})

            if new_pw != confirm_pw:
                return jsonify({"status": "bad", "message": "New passwords do not match"})

            # Verify current password (supports both bcrypt and plain-text legacy)
            stored = self.sql.getadmin_password(session["user_id"])
            if stored is None:
                return jsonify({"status": "bad", "message": "Admin not found"})

            password_ok = False
            try:
                password_ok = self.sql._check(current_pw, stored)
            except Exception:
                password_ok = (current_pw == stored)

            if not password_ok:
                return jsonify({"status": "bad", "message": "Current password is incorrect"})

            try:
                self.sql.updateadmin_password(session["user_id"], new_pw)
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "Failed to update password"})

            return jsonify({"status": "good", "message": "Password updated successfully"})