from flask import Blueprint, render_template, request, jsonify, session, redirect
import json, os
from other.mysql_ import SQL

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "parking.json")


class Admin:
    def __init__(self):
        self.admin = Blueprint("admin", __name__, url_prefix="/admin")
        self.sql = SQL()
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

        # ─── PARKING API ──────────────────────────────────

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
            with open(file_path, "w") as file:
                json.dump(jdata, file, indent=4)
            return jsonify({"status": "ok", "message": "Updated successfully", "total": total})

        # ─── USER MANAGEMENT API ──────────────────────────

        @self.admin.route("/getusers", methods=["GET"])
        def getUsers():
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            users = self.sql.getalluser(limit=limit, offset=offset)
            total = self.sql.countallusers()

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
            return jsonify({"status": "good", "message": "User added successfully"})

        @self.admin.route("/get_qr", methods=["GET"])
        def getqr():
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            data  = self.sql.getallqr(limit=limit, offset=offset)
            total = self.sql.countallqr()
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
            data   = self.sql.get_total_entry_exit()
            scanned = self.sql.get_total_scan()
            return jsonify({
                "entry": data["entry"],
                "exit":  data["exit"],
                "scan":  scanned
            })

        @self.admin.route("/get_history")
        def gethistory():
            page  = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            data  = self.sql.gethistory(limit=limit, offset=offset)
            total = self.sql.counthistory()

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

        # ─── DASHBOARD API ────────────────────────────────

        @self.admin.route("/dashboard_data")
        def dashboard_data():
            parking  = self.sql.getparking()
            entries  = self.sql.get_total_entry_exit()
            active_qr = self.sql.countallqr()
            return jsonify({
                "status":        "good",
                "parking_slots": parking.get("total", 0),
                "occupied":      parking.get("occupied", 0),
                "entered_today": entries["entry"],
                "active_qr":     active_qr
            })

        @self.admin.route("/activity_chart")
        def activity_chart():
            # Placeholder — extend with real weekly data as needed
            return jsonify({"status": "good", "labels": [], "data": []})

        @self.admin.route("/recent_activity")
        def recent_activity():
            rows = self.sql.getallqr(limit=10, offset=0)
            result = []
            for r in rows:
                result.append({
                    "qr_code": r[1],
                    "time":    str(r[8]),
                    "action":  "entry" if r[9] == "IN" else "exit",
                    "plate":   r[2] or "—",
                    "status":  "accepted"
                })
            return jsonify({"status": "good", "data": result})