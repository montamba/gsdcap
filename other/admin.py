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
            users = self.sql.getalluser()
            if users:
                serialized = [
                    [str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in u]
                    for u in users
                ]
                return jsonify({"status": "good", "data": serialized})
            return jsonify({"status": "bad", "message": "No users found"})

        @self.admin.route("/delete_user/<int:id>", methods=["DELETE"])
        def deleteUser(id):
            self.sql.deleteuser(id)
            return jsonify({"status": "ok", "message": "User deleted successfully"})

        @self.admin.route("/add_user", methods=["POST"])
        def add_user():
            data = request.get_json()
            username = data.get("username", "").strip()
            email = data.get("email", "").strip()
            password = data.get("password", "")
            role = data.get("role", "")
            
            isemail = self.sql.getuserbyemail(email)
            username_exist = self.sql.getuserbyusername(username)
            if isemail:
                return jsonify({"status": "bad", "message": "Sorry email already register"})
            
            if username_exist:
                return jsonify({"status": "bad", "message": "Sorry username already register"})
            
            
            
            if not all([username, email, password, role]):
                return jsonify({"status": "bad", "message": "All fields are required"})

            if len(password) < 8:
                return jsonify({"status": "bad", "message": "Password must be at least 8 characters"})

            if self.sql.getuserbyemail(email):
                return jsonify({"status": "bad", "message": f"Email '{email}' is already in use"})

            self.sql.adduser(username, email, password, role)
            return jsonify({"status": "good", "message": "User added successfully"})
        
        @self.admin.route("/get_qr",methods=["GET"])
        def getqr():
            data = self.sql.getallqr()
            ndata = []
            
            for d in data:
                da = [d[1],d[4],d[9]]
                ndata.append(da)
            
            return {
                "status":"good",
                "message":"successfull",
                "data":ndata
            }
            
        @self.admin.route("/get_entries")
        def entries():
            data = self.sql.get_total_entry_exit()
            scanned = self.sql.get_total_scan()
            data["scan"] = scanned
            
            return data
        
        @self.admin.route("/get_history")
        def gethistory():
            data = self.sql.gethistory()
            print(data)
            return data
            
