from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from other.admin import Admin
from other.staff import Staff
from other.guard import Guard
from functools import wraps
import mysql.connector as mysql
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))
            if role and session.get("role") != role:
                return jsonify({"status": "forbidden", "message": "Access denied"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


class Main:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get("SECRET_KEY", "gsd-parking-secret-change-in-prod")
        self.app.config["SESSION_COOKIE_HTTPONLY"] = True
        self.app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

        self.sql = mysql.connect(
            user= os.getenv("USER"),
            host= os.getenv("LOCALHOST"),
            database= os.getenv("DATABASE"),
            passwd= os.getenv("PASSW")
        )
        
        print(os.getenv("DATABASE"))
        self.blueprints()

    def routes(self):
        @self.app.route("/")
        def index():
            if "user_id" in session:
                role = session.get("role")
                if role == "admin":
                    return redirect(url_for("admin.dashboard"))
                else:
                    return redirect("/staff/generate")
            return render_template("index.html")

        # ─── LOGIN --------------------------------------------------------
        @self.app.route("/auth/login", methods=["POST"])
        def login():
            data = request.get_json()
            email = data.get("email").strip()
            password = data.get("password")
            role = data.get("role")
            
            print(0000000000000)
            print(role)
            

            if not email or not password or not role:
                return jsonify({"status": "failed", "message": "Missing required fields"})

            cur = self.sql.cursor()

            user = None
            if role == "admin":
                cur.execute(
                    "SELECT id, email, password FROM admin WHERE email=%s",
                    (email,)
                )
            elif role in ("users", "guard", "staff"):
                cur.execute(
                    "SELECT id, email, password, role FROM users WHERE email=%s AND role=%s",
                    (email,role)
                )

            
            user = cur.fetchone()

            if not user:
                return jsonify({"status": "failed", "message": "Invalid credentials"})
            
            if role == "admin":
                user = user + ('admin',)
            cur.close()

            user_id, user_email, hashed_pw, user_role = user

            password_matches = False
            try:
                password_matches = bcrypt.checkpw(
                    password.encode("utf-8"),
                    hashed_pw.encode("utf-8") if isinstance(hashed_pw, str) else hashed_pw
                )
            except Exception:
                
                password_matches = (password == hashed_pw)

            if not password_matches:
                return jsonify({"status": "failed", "message": "Invalid credentials"})

            session.clear()
            session["user_id"] = user_id
            session["email"] = user_email
            session["role"] = user_role
            session.permanent = False

            return jsonify({"status": "Success", "message": "Login successful", "role": user_role})

        @self.app.route("/auth/logout")
        def logout():
            session.clear()
            return redirect(url_for("index"))

        @self.app.route("/auth/test", methods=["POST"])
        def test():
            return jsonify({"success": True})

        @self.app.route("/auth/me")
        def me():
            if "user_id" not in session:
                return jsonify({"status": "unauthenticated"})
            return jsonify({
                "status": "ok",
                "user_id": session["user_id"],
                "email": session["email"],
                "role": session["role"]
            })

    def blueprints(self):
        self.app.register_blueprint(Admin().admin)
        self.app.register_blueprint(Staff().staff)
        self.app.register_blueprint(Guard().guard)

    def run(self):
        self.app.run(debug=True)


app_instance = Main()

if __name__ == "__main__":
    app_instance.routes()
    app_instance.run()
