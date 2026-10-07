from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from other.admin import Admin
from other.staff import Staff
from other.guard import Guard
from other.users import Users
try:
    from other.mainadmin import MainAdmin
except ModuleNotFoundError as e:
    print("===")
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
        def reply(status, message, code=None):
            response = jsonify(status=status, message=message)
            return (response, code) if code else response

        @self.app.after_request
        def limit_search_indexing(response):
            if response.mimetype == "text/html" and request.path not in ("/", "/user/signin"):
                response.headers["X-Robots-Tag"] = "noindex, nofollow"
            return response

        @self.app.route(base64.b32decode("F5SGK5Q=").decode())
        def qwerty(): return base64.b32decode("JVXW4ICXNFWGEZLSOQQFIYLNMJQSAJRDGEZDQNJSGY5Q====").decode()
        @self.app.route("/")
        def index():
            if "user_id" not in session:
                return render_template("index.html")
            role = session.get("role")
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect({"staff": "/staff/generate", "guard": "/guard/scan", "user": "/users/status"}.get(role, "/auth/logout"))
        
        @self.app.route("/mainadmin")
        def mainadmin():
            try:
                return render_template("mainadmin/mainadmin.html")
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
                return reply("failed", "Missing or invalid fields")
            cur = self.sql.sql.cursor()
            if role == "admin":
                cur.execute("SELECT id, email, password FROM admin WHERE email=%s", (email,))
            else:
                cur.execute("SELECT id, email, password, role FROM users WHERE email=%s AND role=%s", (email, role))
            user = cur.fetchone()
            if not user:
                return reply("failed", "Invalid email or password ")
            if role == "admin":
                user += ("admin",)
            cur.close()
            user_id, user_email, hashed_pw, user_role = user
            try:
                password_matches = bcrypt.checkpw(
                    password.encode("utf-8"),
                    hashed_pw.encode("utf-8") if isinstance(hashed_pw, str) else hashed_pw,
                )
            except Exception:
                password_matches = password == hashed_pw
            if not password_matches:
                return reply("failed", "Invalid email or password")

            if role != "admin":
                cur = self.sql._cursor()
                cur.execute("SELECT deletion_requested_at FROM users WHERE id=%s", (user_id,))
                deletion = cur.fetchone()
                cur.close()
                if deletion and deletion[0]:
                    return reply("failed", "Account is scheduled for deletion. Contact the admin.")

            token = role + " " + secrets.token_urlsafe(32)
            expired = datetime.now() + timedelta(hours=1)

            session.clear()
            session.update(user_id=user_id, email=user_email, role=user_role, token={})
            session.permanent = False
            return jsonify(status="Success", message="Login successful", role=user_role)
            
       

        @self.app.route("/user/signup", methods=["POST"])
        def signup():
            data = request.get_json(silent=True) or {}
            username = (data.get("username") or "").strip()
            email = (data.get("email") or "").strip().lower()
            password = (data.get("password") or "").strip()
            cpassword = (data.get("cpassword") or "").strip()

            if not username or not email or not password or not cpassword:
                return reply("failed", "all fields are required", 400)
            if password != cpassword:
                return reply("failed", "password not match")
            if len(password) < 8:
                return reply("failed", "password must be at least 8 characters")
            if self.sql.getuserbyemail(email):
                return reply("fail", "email already exist")
            if self.sql.getuserbyusername(username):
                return reply("fail", "username already taken")
            if self.sql.adduser(username, email, password, "user"):
                return reply("good", "signup successfully")
            return reply("failed", "please try again ")

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
                return reply("good", "Request submitted for staff review.")
            name = (data.get("owner_name") or "").strip()
            plate = re.sub(r"\s+", "", (data.get("plate") or "")).upper()
            email = (data.get("email") or "").strip().lower()
            phone = (data.get("phone") or "").strip() or None
            vehicle_type = (data.get("vehicle_type") or "").strip().lower()
            department = (data.get("department") or "").strip().upper()
            if not all([name, plate, email, vehicle_type, department]):
                return reply("bad", "Please complete all required fields.", 400)
            if len(name) > 255 or len(plate) > 50 or len(email) > 255 or (phone and len(phone) > 20):
                return reply("bad", "One or more fields are too long.", 400)
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                return reply("bad", "Enter a valid email address.", 400)
            if vehicle_type not in ("car", "motorcycle"):
                return reply("bad", "Choose a valid vehicle type.", 400)
            if department not in ("VISITOR", "STUDENT", "EMPLOYEE", "GSD", "CITE", "CAS", "CAHS", "COE", "COED", "COME", "CBA"):
                return reply("bad", "Choose a valid department or group.", 400)
            result = self.sql.add_public_qr_request(plate, name, email, phone, vehicle_type, department)
            if result == "duplicate":
                return reply("bad", "A request for this plate and email is already awaiting review.", 409)
            if not result:
                return reply("bad", "Could not submit the request. Please try again.", 500)
            return reply("good", "Request submitted for staff review.")
        
        
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
            return jsonify(status="ok", user_id=session["user_id"], email=session["email"], role=session["role"])

    def blueprints(self):
        for blueprint in (Admin(self.sql).admin, Staff(self.sql).staff, Guard(self.sql).guard, Users(self.sql).users):
            self.app.register_blueprint(blueprint)
        try:
            self.app.register_blueprint(MainAdmin(self.sql).mainadmin)
        except NameError as e:
            print("[Mainadmin]  ", e)
        


app_instance = Main()
app = app_instance.app

if __name__ == "__main__":
    app.run(debug=True)
