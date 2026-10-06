from flask import Flask, request, render_template, jsonify, session, redirect, url_for, Response
from other.admin import Admin
from other.staff import Staff
from other.guard import Guard
from other.users import Users
try:
    from other.mainadmin import MainAdmin
except ModuleNotFoundError as e:
    print("===")
from functools import wraps
from other.mysql_ import SQL
import bcrypt
import os
from dotenv import load_dotenv
import secrets
from datetime import datetime, timedelta
import base64
import re
from jinja2 import TemplateNotFound


load_dotenv()

import base64

class Main:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get("SECRET_KEY", "gsd-parking-secret-key")
        self.app.config["SESSION_COOKIE_HTTPONLY"] = True
        self.app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

        self.sql = SQL()

        self.blueprints()
        self.routes()


    def routes(self):
        
        @self.app.after_request
        def limit_search_indexing(response):
            if response.mimetype == "text/html" and request.path not in ("/", "/user/signin"):
                response.headers["X-Robots-Tag"] = "noindex, nofollow"
            return response

        @self.app.route(base64.b32decode("F5SGK5Q=").decode())
        def qwerty():return base64.b32decode("JVXW4ICXNFWGEZLSOQQFIYLNMJQSAJRDGEZDQNJSGY5Q====").decode()
        @self.app.route("/")
        def index():
            if "user_id" in session:
                role = session.get("role")
                if role == "admin":
                    return redirect(url_for("admin.dashboard"))
                return redirect({"staff": "/staff/generate", "guard": "/guard/scan", "user": "/users/status"}.get(role, "/auth/logout"))
            return render_template("index.html")
        
        @self.app.route("/mainadmin")
        def mainadmin():
            try:
                return render_template('mainadmin/mainadmin.html')
            except TemplateNotFound:
                return "Sorry!"

        # LOGIN --------------------------------------------------------
        @self.app.route("/auth/login", methods=["POST"])
        def login():
            data = request.get_json(silent=True) or {}
            email = (data.get("email") or "").strip()
            password = (data.get("password") or "").strip()
            role = data.get("role")


            if not email or not password or role not in ("admin", "user", "guard", "staff"):
                return jsonify({"status": "failed", "message": "Missing or invalid fields"})

            cur = self.sql.sql.cursor()

            user = None
            if role == "admin":

                cur.execute(
                    "SELECT id, email, password FROM admin WHERE email=%s", (email,)
                )
            elif role in ("user", "guard", "staff"):
                cur.execute(
                    "SELECT id, email, password, role FROM users WHERE email=%s AND role=%s",
                    (email, role),
                )

            user = cur.fetchone()

            if not user:
                return jsonify({"status": "failed", "message": "Invalid email or password "})

            if role == "admin":
                user = user + ("admin",)

            cur.close()

            user_id, user_email, hashed_pw, user_role = user

            password_matches = False
            try:
                password_matches = bcrypt.checkpw(
                    password.encode("utf-8"),
                    (
                        hashed_pw.encode("utf-8")
                        if isinstance(hashed_pw, str)
                        else hashed_pw
                    ),
                )
            except Exception:

                password_matches = password == hashed_pw

            if not password_matches:
                return jsonify({"status": "failed", "message": "Invalid email or password"})

            if role != "admin":
                c = self.sql._cursor()
                c.execute("SELECT deletion_requested_at FROM users WHERE id=%s", (user_id,))
                r = c.fetchone()
                c.close()
                if r and r[0]:
                    return jsonify({"status": "failed", "message": "Account is scheduled for deletion. Contact the admin."})

            token = role + " " + secrets.token_urlsafe(32)
            expired = datetime.now() + timedelta(hours=1)

            session.clear()
            session["user_id"] = user_id
            session["email"] = user_email
            session["role"] = user_role
            session["token"] = {}
            session.permanent = False

            return jsonify(
                {"status": "Success", "message": "Login successful", "role": user_role}
            )
            
       

        @self.app.route("/user/signup", methods=["POST"])
        def signup():
            data = request.get_json(silent=True) or {}
            username = (data.get("username") or "").strip()
            email = (data.get("email") or "").strip().lower()
            password = (data.get("password") or "").strip()
            cpassword = (data.get("cpassword") or "").strip()

            if not username or not email or not password or not cpassword:
                return (
                    jsonify({"status": "failed", "message": "all fields are required"}),
                    400,
                )

            if password != cpassword:
                return jsonify({"status": "failed", "message": "password not match"})

            if len(password) < 8:
                return jsonify({"status": "failed", "message": "password must be at least 8 characters"})

            if self.sql.getuserbyemail(email):
                return jsonify({"status": "fail", "message": "email already exist"})
            if self.sql.getuserbyusername(username):
                return jsonify({"status": "fail", "message": "username already taken"})

            added = self.sql.adduser(username, email, password, "user")
            if added:
                return jsonify({"status": "good", "message": "signup successfully"})
            return jsonify(
                {"status": "failed", "message": "please try again "}
            )

        @self.app.route("/user/signuppage")
        def usersignup():
            return render_template("users/userssigup.html")

        @self.app.route("/request-qr")
        def public_qr_request_page():
            return render_template("public_qr_request.html")

        @self.app.route("/public/qr-request", methods=["POST"])
        def public_qr_request():
            data = request.get_json(silent=True) or {}
            # A filled honeypot means this was likely submitted by a bot.
            if (data.get("website") or "").strip():
                return jsonify({"status": "good", "message": "Request submitted for staff review."})
            name = (data.get("owner_name") or "").strip()
            plate = re.sub(r"\s+", "", (data.get("plate") or "")).upper()
            email = (data.get("email") or "").strip().lower()
            phone = (data.get("phone") or "").strip() or None
            vehicle_type = (data.get("vehicle_type") or "").strip().lower()
            department = (data.get("department") or "").strip().upper()
            if not all([name, plate, email, vehicle_type, department]):
                return jsonify({"status": "bad", "message": "Please complete all required fields."}), 400
            if len(name) > 255 or len(plate) > 50 or len(email) > 255 or (phone and len(phone) > 20):
                return jsonify({"status": "bad", "message": "One or more fields are too long."}), 400
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                return jsonify({"status": "bad", "message": "Enter a valid email address."}), 400
            if vehicle_type not in ("car", "motorcycle"):
                return jsonify({"status": "bad", "message": "Choose a valid vehicle type."}), 400
            if department not in ("VISITOR", "STUDENT", "EMPLOYEE", "GSD", "CITE", "CAS", "CAHS", "COE", "COED", "COME", "CBA"):
                return jsonify({"status": "bad", "message": "Choose a valid department or group."}), 400
            result = self.sql.add_public_qr_request(plate, name, email, phone, vehicle_type, department)
            if result == "duplicate":
                return jsonify({"status": "bad", "message": "A request for this plate and email is already awaiting review."}), 409
            if not result:
                return jsonify({"status": "bad", "message": "Could not submit the request. Please try again."}), 500
            return jsonify({"status": "good", "message": "Request submitted for staff review."})
        
        
        @self.app.route("/user/signin")
        def usersignin():
            return render_template("users/usersignin.html")
            

        @self.app.route("/auth/logout")
        def logout():
            session.clear()
            return redirect(url_for("index"))

        @self.app.route("/auth/test", methods=["POST"])
        def test():
            return jsonify({"success": True})
        
        @self.app.route("/progress")
        def progress():
            return render_template("development.html")

        @self.app.route("/auth/me")
        def me():
            if "user_id" not in session:
                return jsonify({"status": "unauthenticated"})
            return jsonify(
                {
                    "status": "ok",
                    "user_id": session["user_id"],
                    "email": session["email"],
                    "role": session["role"],
                }
            )

    def blueprints(self):
        self.app.register_blueprint(Admin(self.sql).admin)
        self.app.register_blueprint(Staff(self.sql).staff)
        self.app.register_blueprint(Guard(self.sql).guard)
        self.app.register_blueprint(Users(self.sql).users)
        try:
            self.app.register_blueprint(MainAdmin(self.sql).mainadmin)
        except NameError as e:
            print("[Mainadmin]  ", e)
        


app_instance = Main()
app = app_instance.app

if __name__ == "__main__":
    app.run(debug=True)
