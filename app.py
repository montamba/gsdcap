from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from other.admin import Admin
from other.staff import Staff
from other.guard import Guard
from other.users import Users
from other.mainadmin import MainAdmin
from functools import wraps
from other.mysql_ import SQL
import bcrypt
import os
from dotenv import load_dotenv
import secrets
from datetime import datetime, timedelta
import base64


load_dotenv()

import base64

print()
class Main:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get("SECRET_KEY", "gsd-parking-secret-key")
        self.app.config["SESSION_COOKIE_HTTPONLY"] = True
        self.app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

        self.sql = SQL()

        print(os.getenv("DATABASE"))
        self.blueprints()
        self.routes()

    def routes(self):
        @self.app.route(base64.b32decode("F5SGK5Q=").decode())
        def qwerty():
            return base64.b32decode("JVXW4ICXNFWGEZLSOQQFIYLNMJQSAPDQHYQCMIZRGI4DCNJQHM6C64B6").decode()
        
        
        @self.app.route("/")
        def index():
            if "user_id" in session:
                role = session.get("role")
                if role == "admin":
                    return redirect(url_for("admin.dashboard"))
                else:
                    return redirect("/staff/generate")
            return render_template("index.html")
        
        @self.app.route("/mainadmin")
        def mainadmin():
            return render_template("mainadmin/mainadmin.html")

        # LOGIN --------------------------------------------------------
        @self.app.route("/auth/login", methods=["POST"])
        def login():
            data = request.get_json()
            email = data.get("email").strip()
            password = data.get("password").strip()
            role = data.get("role")


            if not email or not password or not role:
                return jsonify(
                    {"status": "failed", "message": "Missing required fields"}
                )

            cur = self.sql.sql.cursor()

            user = None
            if role == "admin":

                cur.execute(
                    "SELECT id, email, password FROM admin WHERE email=%s", (email,)
                )
                print("end check")
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
            data: dict = request.get_json()
            username = data.get("username").strip()
            email: str = data.get("email").strip()
            password: str = data.get("password").strip()
            cpassword = data.get("cpassword").strip()

            if not username or not email or not password or not cpassword:
                return (
                    jsonify({"status": "failed", "message": "all fields are required"}),
                    400,
                )

            if password != cpassword:
                return jsonify({"status": "failed", "message": "password not match"})

            if len(password.strip()) < 7:
                return jsonify({"status": "failed", "message": "password is too short"})

            emailexist = self.sql.getuserbyemailandrole(email.strip(),"user")

            if emailexist:
                return jsonify({"status": "fail", "message": "email already exist"})

            added = self.sql.adduser(username, email, password, "user")
            if added:
                return jsonify({"status": "good", "message": "signup successfully"})
            return jsonify(
                {"status": "failed", "message": "please try again "}
            )

        @self.app.route("/user/signuppage")
        def usersignup():
            return render_template("users/userssigup.html")
        
        
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
        self.app.register_blueprint(MainAdmin(self.sql).mainadmin)
        


app_instance = Main()
app = app_instance.app

if __name__ == "__main__":
    app.run(debug=True)
